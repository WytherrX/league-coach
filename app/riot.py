"""Accès à l'API officielle de Riot (Account-V1, Match-V5, League-V4) et extraction des champs d'une partie."""
import datetime
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from zoneinfo import ZoneInfo

API_KEY = os.environ.get("RIOT_API_KEY", "").strip().strip("'\"")  # tolère une clé collée entre guillemets
TZ = ZoneInfo(os.environ.get("TZ") or "Europe/Paris")
RANKED_SOLO = 420

# région du compte -> (serveur de la plateforme, cluster régional)
ROUTING = {
    "euw": ("euw1", "europe"), "eune": ("eun1", "europe"), "tr": ("tr1", "europe"), "ru": ("ru", "europe"),
    "na": ("na1", "americas"), "br": ("br1", "americas"), "lan": ("la1", "americas"), "las": ("la2", "americas"),
    "kr": ("kr", "asia"), "jp": ("jp1", "asia"), "oce": ("oc1", "sea"),
}
TIER_CODE = {"IRON": "I", "BRONZE": "B", "SILVER": "S", "GOLD": "G", "PLATINUM": "P", "EMERALD": "E", "DIAMOND": "D"}
DIVISION = {"I": "1", "II": "2", "III": "3", "IV": "4"}
OBJECTIVES = {"DRAGON", "BARON_NASHOR", "RIFTHERALD", "HORDE", "ATAKHAN"}
# Centre des pits sur la Faille de l'invocateur, si l'événement ne donne pas de position
PITS = {"DRAGON": (9866, 4414), "BARON_NASHOR": (5007, 10471), "RIFTHERALD": (5007, 10471), "HORDE": (5007, 10471)}
NEAR = 3000          # rayon autour du pit, en unités de jeu (environ la largeur de la rivière et des entrées)
FIGHT_BEFORE, FIGHT_AFTER = 30_000, 15_000


def _dist(a, b):
    return ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5


def lost_objectives(timeline, team, allies):
    """Objectifs pris par l'adversaire sans combat : aucun kill près du pit entre 30 s avant et 15 s après,
    et aucun allié près du pit aux relevés de positions (une par minute) qui encadrent la prise."""
    frames = timeline["info"]["frames"]
    events = [e for f in frames for e in f.get("events", [])]
    kills = [e for e in events if e.get("type") == "CHAMPION_KILL"]
    lost, last_grubs = 0, -10**9
    for e in events:
        if e.get("type") != "ELITE_MONSTER_KILL" or e.get("monsterType") not in OBJECTIVES:
            continue
        if e.get("killerTeamId") in (None, team):
            continue
        t = e["timestamp"]
        if e["monsterType"] == "HORDE":  # les larves meurent par groupe : un seul objectif par vague
            if t - last_grubs < 120_000:
                continue
            last_grubs = t
        pit = e.get("position") or ({"x": PITS[e["monsterType"]][0], "y": PITS[e["monsterType"]][1]} if e["monsterType"] in PITS else None)
        fight = any(t - FIGHT_BEFORE <= k["timestamp"] <= t + FIGHT_AFTER and (pit is None or "position" not in k or _dist(k["position"], pit) <= NEAR)
                    for k in kills)
        present = False
        if pit:
            around = [f for f in frames if abs(f["timestamp"] - t) < 60_000]   # le relevé d'avant et celui d'après
            present = any(_dist(f["participantFrames"][str(a)]["position"], pit) <= NEAR
                          for f in around for a in allies if str(a) in f.get("participantFrames", {}) and "position" in f["participantFrames"][str(a)])
        if not fight and not present:
            lost += 1
    return lost


class RiotError(Exception):
    pass


# Limites d'une clé personnelle : 20 requêtes par seconde et 100 toutes les 2 minutes. On reste juste en dessous.
_lock = threading.Lock()
_calls = deque()
LIMITS = [(18, 1.0), (95, 120.0)]


def _wait_turn():
    with _lock:
        while True:
            now = time.monotonic()
            while _calls and now - _calls[0] > max(w for _, w in LIMITS):
                _calls.popleft()
            delay = 0
            for n, window in LIMITS:
                recent = [t for t in _calls if now - t < window]
                if len(recent) >= n:
                    delay = max(delay, window - (now - recent[-n]) + 0.05)
            if not delay:
                _calls.append(now)
                return
            time.sleep(delay)


def get(url):
    """GET authentifié, avec respect du débit et des réponses 429. Renvoie le JSON décodé, ou None sur 404."""
    if not API_KEY:
        raise RiotError("RIOT_API_KEY absente du fichier .env")
    for _ in range(4):
        _wait_turn()
        req = urllib.request.Request(url, headers={"X-Riot-Token": API_KEY, "User-Agent": "league-coach"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429 or e.code >= 500:
                time.sleep(int(e.headers.get("Retry-After") or 5))
                continue
            if e.code in (401, 403):
                raise RiotError("Clé API Riot refusée (expirée ou invalide) : vérifie RIOT_API_KEY dans .env")
            raise RiotError(f"Erreur API Riot {e.code}")
        except (urllib.error.URLError, TimeoutError) as e:
            raise RiotError(f"API Riot injoignable : {getattr(e, 'reason', e)}")
    raise RiotError("API Riot saturée, nouvel essai à la prochaine synchronisation")


def hosts(region):
    platform, regional = ROUTING.get(region, ROUTING["euw"])
    return f"https://{platform}.api.riotgames.com", f"https://{regional}.api.riotgames.com"


def puuid(riot_id, region):
    name, _, tag = riot_id.partition("#")
    _, base = hosts(region)
    base = base.replace("sea.", "asia.")  # Account-V1 n'existe pas sur le cluster SEA
    # safe="" : un « / » dans le Riot ID est encodé et ne peut pas modifier le chemin de la requête
    acc = get(f"{base}/riot/account/v1/accounts/by-riot-id/{urllib.parse.quote(name.strip(), safe='')}/{urllib.parse.quote(tag.strip(), safe='')}")
    if not acc:
        raise RiotError(f"Riot ID introuvable : {riot_id}")
    return acc["puuid"]


def match_ids(pid, region, count=20):
    _, base = hosts(region)
    return get(f"{base}/lol/match/v5/matches/by-puuid/{pid}/ids?queue={RANKED_SOLO}&type=ranked&start=0&count={count}") or []


def match(mid, region):
    _, base = hosts(region)
    return get(f"{base}/lol/match/v5/matches/{mid}"), get(f"{base}/lol/match/v5/matches/{mid}/timeline")


def solo_rank(pid, region):
    """Rang solo/duo actuel au format de l'appli (D3, M, GM, C), LP et nombre total de parties classées de la saison.
    (None, None, None) si non classé."""
    platform, _ = hosts(region)
    for e in get(f"{platform}/lol/league/v4/entries/by-puuid/{pid}") or []:
        if e.get("queueType") == "RANKED_SOLO_5x5":
            tier = e["tier"]
            div = {"MASTER": "M", "GRANDMASTER": "GM", "CHALLENGER": "C"}.get(tier)
            if not div and tier in TIER_CODE:
                div = TIER_CODE[tier] + DIVISION.get(e.get("rank"), "4")
            return div, e.get("leaguePoints"), e.get("wins", 0) + e.get("losses", 0)
    return None, None, None


def frame_at(timeline, minute):
    """Relevé de la chronologie à la minute donnée (un relevé par minute), ou None si la partie a fini avant."""
    frames = timeline["info"]["frames"] if timeline else []
    return frames[minute] if len(frames) > minute else None


POSITIONS = {"TOP": "top", "JUNGLE": "jungle", "MIDDLE": "mid", "BOTTOM": "adc", "UTILITY": "support"}


def parse_game(m, timeline, pid):
    """Transforme une partie Match-V5 et sa chronologie en ligne de la table games, quel que soit le rôle joué :
    le rôle vient du poste attribué par Riot (teamPosition), l'adversaire est le joueur du même poste en face.
    Renvoie (game, raison) : game vaut None si la partie est ignorée (remake, poste inconnu)."""
    info = m["info"]
    me = next((p for p in info["participants"] if p["puuid"] == pid), None)
    if not me:
        return None, "absent"
    duration = info["gameDuration"] if "gameEndTimestamp" in info else info["gameDuration"] / 1000
    if duration < 300 or me.get("gameEndedInEarlySurrender"):
        return None, "remake"
    position = me.get("teamPosition") or me.get("individualPosition")
    if position not in POSITIONS:
        return None, "poste inconnu"
    team = me["teamId"]
    enemy = next((p for p in info["participants"] if p["teamId"] != team and (p.get("teamPosition") or p.get("individualPosition")) == position), None)

    team_kills = sum(p["kills"] for p in info["participants"] if p["teamId"] == team)
    kp = me.get("challenges", {}).get("killParticipation")
    if kp is None:
        kp = (me["kills"] + me["assists"]) / team_kills if team_kills else 0

    deaths_pre15, obj_lost = 0, 0
    if timeline:
        events = [e for f in timeline["info"]["frames"] for e in f.get("events", [])]
        deaths_pre15 = sum(1 for e in events if e.get("type") == "CHAMPION_KILL"
                           and e.get("victimId") == me["participantId"] and e["timestamp"] < 15 * 60 * 1000)
        allies = [p["participantId"] for p in info["participants"] if p["teamId"] == team]
        obj_lost = lost_objectives(timeline, team, allies)

    # Part des dégâts infligés aux champions dans l'équipe
    share = me.get("challenges", {}).get("teamDamagePercentage")
    if share is None:
        team_dmg = sum(p.get("totalDamageDealtToChampions", 0) for p in info["participants"] if p["teamId"] == team)
        share = me.get("totalDamageDealtToChampions", 0) / team_dmg if team_dmg else None
    # CS à 10 min et écart d'or à 15 min face à l'adversaire du même poste, depuis les relevés de la chronologie
    cs10 = gd15 = None
    f10, f15 = frame_at(timeline, 10), frame_at(timeline, 15)
    mine = str(me["participantId"])
    if f10 and mine in f10.get("participantFrames", {}):
        pf = f10["participantFrames"][mine]
        cs10 = pf.get("minionsKilled", 0) + pf.get("jungleMinionsKilled", 0)
    if f15 and enemy and mine in f15.get("participantFrames", {}) and str(enemy["participantId"]) in f15["participantFrames"]:
        gd15 = f15["participantFrames"][mine].get("totalGold", 0) - f15["participantFrames"][str(enemy["participantId"])].get("totalGold", 0)

    start = info.get("gameStartTimestamp") or info["gameCreation"]
    return {
        "match_id": m["metadata"]["matchId"],
        "played_on": datetime.datetime.fromtimestamp(start / 1000, TZ).date().isoformat(),
        "played_at": start,
        "champ": me["championName"].lower(),
        "enemy": enemy["championName"].lower() if enemy else None,
        "result": "W" if me["win"] else "L",
        "kills": me["kills"], "deaths": me["deaths"], "assists": me["assists"],
        "deaths_pre15": deaths_pre15 if timeline else None,
        "kp": round(100 * kp),
        "cs_min": round((me.get("totalMinionsKilled", 0) + me.get("neutralMinionsKilled", 0)) / (duration / 60), 1),
        "control_wards": me.get("visionWardsBoughtInGame"),
        "obj_lost_free": obj_lost if timeline else None,
        "cs10": cs10,
        "gd15": gd15,
        "dmg_share": round(100 * share) if share is not None else None,
        "vision_min": round(me["visionScore"] / (duration / 60), 2) if me.get("visionScore") is not None else None,
        "role": POSITIONS[position],
    }, None
