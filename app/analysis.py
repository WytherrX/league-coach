import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
VOLUME_DIR = os.path.dirname(os.environ.get("DB_PATH", "/data/x"))


def override_path(role):
    """Fichier de matchups importé depuis la page Admin, conservé dans le volume de données."""
    return os.path.join(VOLUME_DIR, ROLES[role]["file"])

TIERS = [("I", "Fer"), ("B", "Bronze"), ("S", "Argent"), ("G", "Or"), ("P", "Platine"), ("E", "Émeraude"), ("D", "Diamant")]
RANKS = [f"{t}{d}" for t, _ in TIERS for d in (4, 3, 2, 1)] + ["M", "GM", "C"]

# ---------- Rôles ----------
# Chaque rôle a ses indicateurs (clé, libellé, unité, cible, seuil d'alerte, plus haut = mieux),
# ses exercices par indicateur, son fichier de matchups et ses textes.

POOL_DRILL = [("p-pool", "Rester dans ton pool", ["Ne jouer que des champions à 3/5 d'aisance ou plus", "Utiliser la page Counters pour choisir", "Garder les champions en apprentissage pour les parties normales"])]

JUNGLE = {
    "label": "Jungle", "short": "JUNGLE", "position": "JUNGLE", "file": "matchups.json",
    "enemy": "Jungler adverse", "enemy_q": "Quel jungler en face ?", "champs_label": "Tous les junglers",
    "aggressive": {"xinzhao", "jarvaniv", "trundle", "shaco", "nidalee", "leesin", "elise", "reksai", "graves",
                   "vi", "volibear", "pantheon", "darius", "rengar", "kindred", "qiyana", "naafiri", "talon"},
    "aggr_label": "Jungler early agressif", "calm_label": "Jungler de tempo / scaling", "plan_title": "Plan de début de partie",
    "plan_aggr": ["Pas de duel avant ton premier objet.", "Démarre du côté où tes lanes ont la priorité.",
                  "Ward ton buff ou ta deuxième entrée vers 3:00.", "S'il gank une lane, contre-gank ou prends ses camps de l'autre côté."],
    "plan_calm": ["Repère son côté de départ au leash et anticipe son premier gank.", "S'il veut farmer et scaler, force-le à jouer autour de tes ganks.",
                  "Invade son deuxième camp quand tes lanes du côté ont la priorité.", "Prépare le premier objectif 90 secondes avant son apparition."],
    "charts": [("kp", "Participation aux kills", 60, 20, 90, "cible 60 %"), ("deaths", "Morts par partie", 4.5, 0, 12, "cible 4,5")],
    "form": ["obj_lost_free"],
    "metrics": [
        ("kp", "Participation aux kills", "%", 60, 55, True),
        ("deaths", "Morts par partie", "", 4.5, 5.5, False),
        ("deaths_pre15", "Morts avant 15 min", "", 1.5, 2.5, False),
        ("cs_min", "CS par minute", "", 6.5, 6.0, True),
        ("control_wards", "Control wards", "", 2, 1, True),
        ("obj_lost_free", "Objectifs perdus sans combat", "", 1, 2, False),
        ("pool_share", "Parties sur ton pool", "%", 80, 60, True),
    ],
    "drills": {
        "kp": [
            ("kp-track", "Tracker le jungler adverse", ["Au leash, noter son côté de départ probable", "Prévoir l'heure et la lane de son premier gank", "Ping la lane concernée 20 s avant"]),
            ("kp-cross", "Jouer à l'opposé du jungler adverse", ["Quand il se montre d'un côté, partir de l'autre", "Prendre un objectif, un invade ou un gank en échange", "Ne jamais arriver en 2v3 en retard"]),
            ("kp-30s", "Anticiper les fights", ["Avant chaque camp après 6 min : un fight peut-il éclater dans les 30 s ?", "Si oui, se placer au lieu de farmer", "Viser 60 % de participation"]),
        ],
        "deaths": [
            ("d-second", "Entrer en fight en second", ["Attendre l'engage d'un allié", "Entrer sur le flanc", "Aucun engage seul sans info sur 3 adversaires"]),
            ("d-vision", "Pas d'invade à l'aveugle", ["Entrer dans la jungle adverse seulement avec vision ou info", "Sortir dès que 2 adversaires disparaissent de la carte", "Viser 4 morts maximum"]),
            ("d-reset", "Reset au bon moment", ["Reset sous 40 % de vie ou sans sorts", "Reset avant chaque objectif plutôt que pendant", "Ne pas finir un camp à 20 % de vie près de l'adversaire"]),
        ],
        "deaths_pre15": [
            ("e-plan", "Plan de début de partie fixé", ["Au chargement : full clear ou 3 camps puis gank, et de quel côté", "Décider la lane à ganker selon le CC et la wave", "S'y tenir jusqu'à 3:30"]),
            ("e-contest", "Pas de contest sans allié", ["Face à un jungler early, scuttle et camps seulement avec un allié proche", "Ward ton buff ou ta deuxième entrée vers 3:00", "Contre-ganker plutôt que défendre seul"]),
            ("e-duel", "Pas de duel avant le premier objet", ["Si ton champion est plus faible early, éviter le 1v1", "Jouer pour le niveau 6 et le premier objet", "Prendre le contrôle ensuite"]),
        ],
        "cs_min": [
            ("cs-clear", "Clear optimisé", ["Full clear chronométré en partie d'entraînement", "Le reproduire en ranked", "Aucun camp oublié avant 6 min"]),
            ("cs-path", "Repasser par les camps", ["Après chaque gank ou objectif, reprendre les camps réapparus", "Garder les timers de camps en tête", "Viser 6,5 CS/min"]),
            ("cs-wave", "Prendre les vagues libres", ["Quand tes camps sont vides, prendre une vague latérale sûre", "Seulement si 3 adversaires sont visibles ailleurs", "Revenir dans la jungle avant le prochain objectif"]),
        ],
        "control_wards": [
            ("cw-buy", "Control wards à chaque reset", ["Acheter 2 control wards à chaque retour si tu as la place", "En poser une avant de quitter la base", "Viser 3 par partie"]),
            ("cw-obj", "Vision avant objectif", ["Control ward dans la fosse 60 s avant l'objectif", "Ward profonde sur le chemin du jungler adverse", "Nettoyer la vision adverse avec l'Oracle Lens"]),
        ],
        "obj_lost_free": [
            ("o-90", "Préparer l'objectif à 90 s", ["90 s avant : reset si besoin", "60 s avant : vision dans et autour de la fosse", "45 s avant : ping des lanes qui doivent pousser"]),
            ("o-trade", "Échanger quand on ne peut pas contester", ["Sans priorité, ne pas lancer l'objectif", "Prendre une tour, des camps ou un autre objectif de l'autre côté", "Ne jamais perdre un objectif sans rien prendre en échange"]),
        ],
        "pool_share": POOL_DRILL,
        "close": [
            ("c-decide", "Fermer les parties", ["Après un fight gagné, choisir Baron, tour ou reset avant de bouger", "Le pinger à l'équipe", "Après 20 min, ne plus farmer seul dans la jungle adverse sans vision"]),
        ],
    },
}

ADC = {
    "label": "ADC", "short": "ADC", "position": "BOTTOM", "file": "matchups-adc.json",
    "enemy": "ADC adverse", "enemy_q": "Quel ADC en face ?", "champs_label": "Tous les ADC",
    "aggressive": {"draven", "lucian", "kalista", "caitlyn", "samira", "tristana", "nilah", "missfortune", "ziggs", "varus", "yasuo"},
    "aggr_label": "Lane agressive", "calm_label": "Lane de farm / scaling", "plan_title": "Plan de lane",
    "plan_aggr": ["Ne lui laisse pas le niveau 2 en premier : last-hit la 7e sbire de la vague 2 en même temps que lui ou recule.",
                  "Laisse la vague pousser vers ta tour et farm en sécurité plutôt que d'échanger.",
                  "Ward le tribush ou la rivière à 2:45 : sa lane gagne surtout avec son jungler.",
                  "Joue pour ton premier objet et les fights à 4 ou 5 : c'est là que tu le dépasses."],
    "plan_calm": ["Prends le niveau 2 en premier et échange tout de suite avec ton support.",
                  "Frappe-le à chaque fois qu'il va chercher un sbire.",
                  "Pousse pour les plaques et le premier back avec avance d'or.",
                  "Garde la priorité de vague 60 s avant chaque dragon."],
    "charts": [("cs_min", "CS par minute", 8.0, 4, 11, "cible 8"), ("deaths", "Morts par partie", 4.0, 0, 12, "cible 4")],
    "form": ["cs10", "gd15", "dmg_share"],
    "metrics": [
        ("cs_min", "CS par minute", "", 8.0, 7.2, True),
        ("cs10", "CS à 10 min", "", 80, 70, True),
        ("gd15", "Écart d'or à 15 min", "or", 0, -400, True),
        ("deaths", "Morts par partie", "", 4.0, 5.0, False),
        ("deaths_pre15", "Morts avant 15 min", "", 1.0, 1.5, False),
        ("dmg_share", "Part des dégâts de l'équipe", "%", 27, 23, True),
        ("kp", "Participation aux kills", "%", 50, 45, True),
        ("control_wards", "Control wards", "", 1.5, 1, True),
        ("pool_share", "Parties sur ton pool", "%", 80, 60, True),
    ],
    "drills": {
        "cs_min": [
            ("a-cs-last", "Last-hit propre sous la tour", ["Sbire de mêlée : 2 coups de tour puis 1 auto", "Sbire distance : 1 auto avant le coup de tour, 1 après", "Partie d'entraînement : 80 CS à 10 min sans sorts"]),
            ("a-cs-side", "Récupérer les vagues latérales", ["Après la première tour bot, aller chercher la vague mid ou top la plus proche", "Seulement si l'ADC et le support adverses sont visibles", "Revenir pour chaque objectif 45 s avant"]),
            ("a-cs-reset", "Back sans perdre de vague", ["Pousser la vague dans la tour avant chaque back", "Revenir avant que la vague suivante n'arrive", "Ne jamais back avec une vague qui arrive sur ta tour"]),
        ],
        "cs10": [
            ("a-l10-wave", "Vagues des 3 premières minutes", ["Vague 1 : ne pas pousser, prendre seulement les last-hits", "Vague 2 : préparer le niveau 2 sur la 7e sbire", "Ne lâcher aucun CS de la vague 3"]),
            ("a-l10-trade", "Échanger sans perdre de CS", ["N'échanger que quand aucun sbire n'est à un coup", "Reculer derrière ta vague après l'échange", "Viser 80 CS à 10 min"]),
        ],
        "gd15": [
            ("a-gd-punish", "Punir chaque last-hit adverse", ["Quand l'ADC adverse avance pour un sbire, auto-attaque-le", "Reculer aussitôt derrière ta vague", "Viser un échange gagnant par vague"]),
            ("a-gd-recall", "Back au bon moment", ["Back après avoir poussé la vague, avec l'or d'un composant", "Premier back entre 1 100 et 1 300 or selon ton objet", "Ne jamais rester en lane à 40 % de vie face à un all-in"]),
            ("a-gd-plates", "Prendre les plaques", ["Avec la priorité de vague, frapper la tour plutôt que l'ADC", "Pinger le support avant de pousser", "Reculer dès que le jungler adverse est montré ailleurs depuis plus de 20 s"]),
        ],
        "deaths": [
            ("a-d-pos", "Rester derrière la frontline", ["En fight, frapper la cible la plus proche que tu atteins en sécurité", "Garder ton dash ou ton Flash pour te sauver, pas pour engager", "Ne jamais être le premier visible au milieu de la rivière"]),
            ("a-d-side", "Pas de side lane sans info", ["Push une side lane seulement si 3 adversaires sont visibles", "Ward à mi-chemin avant de dépasser la rivière", "Rentrer dès que 2 adversaires disparaissent"]),
            ("a-d-wait", "Attendre l'engage", ["Laisser ta frontline ou ton support engager", "Entrer dans le fight sur les cibles déjà engagées", "Viser 4 morts maximum"]),
        ],
        "deaths_pre15": [
            ("a-e-jungler", "Respecter le jungler adverse", ["Ward le tribush ou la rivière à 2:45", "S'il n'est pas montré depuis 30 s, ne pas dépasser le milieu de la lane", "Garder le Flash pour son premier gank"]),
            ("a-e-spikes", "Respecter les power spikes", ["Niveau 2, 3 et 6 : savoir lequel l'adversaire atteint en premier", "Reculer d'un pas quand il le prend avant toi", "Ne pas échanger contre un composant qu'il vient d'acheter"]),
        ],
        "dmg_share": [
            ("a-dmg-front", "Frapper ce qui est à portée", ["En fight, auto-attaquer la cible la plus proche plutôt que de chercher le carry", "Ne jamais arrêter de frapper pendant plus de 2 s", "Kiter en arrière, pas sur le côté"]),
            ("a-dmg-group", "Être présent aux fights du milieu de partie", ["Après la phase de lane, se regrouper avec l'équipe pour chaque objectif", "Arriver avec ton objet fini plutôt que de farmer 30 s de plus", "Viser 27 % des dégâts de l'équipe"]),
        ],
        "kp": [
            ("a-kp-rotate", "Bouger avec ton support", ["Après la première tour bot, aller mid avec ton support", "Rejoindre chaque fight à 4 ou 5 qui se prépare autour d'un objectif", "Viser 50 % de participation"]),
        ],
        "control_wards": [
            ("a-cw-river", "Control ward en rivière bot", ["Une control ward dans le bush de rivière ou le tribush dès le premier back", "La remplacer à chaque retour en lane", "Viser 2 par partie"]),
        ],
        "pool_share": POOL_DRILL,
        "close": [
            ("a-c-close", "Fermer les parties", ["Après un fight gagné, frapper la tour la plus proche avec l'équipe", "Ne pas aller farmer seul une vague éloignée", "Toujours finir l'objectif avant de back"]),
        ],
    },
}

ROLES = {"jungle": JUNGLE, "adc": ADC}
DRILLS = {f"{role}:{cat}": ds for role, cfg in ROLES.items() for cat, ds in cfg["drills"].items()}
DRILL_INDEX = {d[0]: (cat, d[1], d[2]) for cat, ds in DRILLS.items() for d in ds}
STAT_KEYS = ("kp", "deaths", "deaths_pre15", "cs_min", "control_wards", "obj_lost_free", "cs10", "gd15", "dmg_share")


def role_of(account):
    return account["role"] if account and account["role"] in ROLES else "jungle"


COMFORT = {5: "Main", 4: "Très à l'aise", 3: "À l'aise", 2: "Correct", 1: "En apprentissage"}
COMFORT_BONUS = {5: 3.0, 4: 1.5, 3: 0.0, 2: -2.0, 1: -4.0}  # points de winrate


def games_bonus(games):
    """Bonus d'expérience selon les parties enregistrées : jamais négatif, pour ne pas pénaliser un main tout juste saisi."""
    if games >= 50:
        return 1.0
    if games >= 20:
        return 0.5
    return 0.0


def mastery_bonus(entry):
    return COMFORT_BONUS.get(entry["comfort"], 0.0) + games_bonus(entry["games"])


MIN_GAMES = 100  # en dessous, une source n'est pas prise en compte pour un matchup


def source_wr(matchups, a, b):
    """Winrate de a contre b dans une source, en lisant l'autre sens si besoin."""
    row = matchups.get(a, {}).get(b)
    if row and row[0]:
        return row[0], row[1] / row[0]
    rev = matchups.get(b, {}).get(a)
    if rev and rev[0]:
        return rev[0], 1 - rev[1] / rev[0]
    return 0, None


def load_matchups(role="jungle"):
    path = override_path(role)
    if not os.path.exists(path):
        path = os.path.join(DATA_DIR, ROLES[role]["file"])
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "sources" not in data:  # ancien format à une seule source
        data["sources"] = {"source": {"label": data.get("source", "source"), "matchups": data["matchups"]}}
    champs = list(data["champions"])
    combined = {}
    for a in champs:
        combined[a] = {}
        for b in champs:
            if a == b:
                continue
            per = {}
            for key, src in data["sources"].items():
                g, wr = source_wr(src["matchups"], a, b)
                if wr is not None and g >= MIN_GAMES:
                    per[key] = (g, wr)
            if per:
                wrs = [wr for _, wr in per.values()]
                combined[a][b] = {"wr": sum(wrs) / len(wrs), "spread": max(wrs) - min(wrs),
                                  "games": max(g for g, _ in per.values()), "per": per}
    totals = {}
    for a in champs:
        overall = []
        for src in data["sources"].values():
            opps = src["matchups"].get(a, {})
            g = sum(v[0] for v in opps.values())
            if g:
                overall.append((sum(v[1] for v in opps.values()) / g, g))
        totals[a] = (100 * sum(o[0] for o in overall) / len(overall), max(o[1] for o in overall)) if overall else (None, 0)
    data["combined"] = combined
    data["totals"] = totals
    data["source_list"] = [(k, v["label"]) for k, v in data["sources"].items()]
    return data


def rank_value(div, lp):
    if not div:
        return None
    if div in ("M", "GM", "C"):
        return len(TIERS) * 400 + (lp or 0)
    tier = [t for t, _ in TIERS].index(div[0])
    return tier * 400 + (4 - int(div[1])) * 100 + (lp or 0)


def rank_label(div, lp=None):
    if not div:
        return "—"
    names = dict(TIERS)
    name = {"M": "Master", "GM": "Grandmaster", "C": "Challenger"}.get(div) or f"{names[div[0]]} {div[1]}"
    return f"{name} · {lp} LP" if lp is not None else name


def avg(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def compute_metrics(games, pool):
    out = {}
    n = len(games)
    out["games"] = n
    out["winrate"] = 100 * sum(1 for g in games if g["result"] == "W") / n if n else None
    for key in STAT_KEYS:
        out[key] = avg([g.get(key) for g in games])
    out["pool_share"] = 100 * sum(1 for g in games if g["champ"] in pool) / n if (n and pool) else None
    tried = [g for g in games if g["focus"] and g["focus_ok"] is not None]
    out["focus_rate"] = 100 * sum(1 for g in tried if g["focus_ok"]) / len(tried) if tried else None
    return out


def status(value, target, warn, higher):
    if value is None:
        return ""
    if higher:
        return "good" if value >= target else "warn" if value >= warn else "bad"
    return "good" if value <= target else "warn" if value <= warn else "bad"


def fmt_metric(v, unit, signed=False):
    if v is None:
        return "—"
    if unit == "%":
        return f"{v:.0f} %"
    if unit == "or":
        return f"{v:+.0f}".replace("-", "−")
    return f"{v:.1f}".replace(".", ",")


def weaknesses(metrics, role="jungle"):
    rows = []
    for key, label, unit, target, warn, higher in ROLES[role]["metrics"]:
        v = metrics.get(key)
        st = status(v, target, warn, higher)
        gap = None
        scale = abs(target) or abs(target - warn)   # cible à 0 (écart d'or) : on mesure en seuils d'alerte
        if v is not None:
            gap = (target - v) / scale if higher else (v - target) / scale
        t = f"{target:+g}".replace("-", "−") if unit == "or" and target else f"{target:g}".replace(".", ",") + (" %" if unit == "%" else "")
        target_txt = ("≥ " if higher else "≤ ") + t
        rows.append({"key": key, "label": label, "unit": unit, "value": v, "target": target, "higher": higher, "status": st,
                     "gap": gap, "display": fmt_metric(v, unit), "target_txt": target_txt,
                     "pct": None if gap is None else max(0.0, min(1.0, 1 - gap))})
    severity = {"bad": 0, "warn": 1, "good": 2, "": 3}
    rows.sort(key=lambda r: (severity[r["status"]], -(r["gap"] or 0)))
    return rows


def next_focus(weak_rows, games, role="jungle"):
    bad = [r for r in weak_rows if r["status"] in ("bad", "warn")]
    cat = bad[0]["key"] if bad else "close"
    history = {}
    for g in games:
        if g["focus"]:
            h = history.setdefault(g["focus"], [0, 0])
            h[0] += 1
            h[1] += 1 if g["focus_ok"] else 0
    def mastered(drill):
        tries, ok = history.get(drill[0], [0, 0])
        return tries >= 3 and ok / tries >= 0.7

    # un exercice pas encore maîtrisé d'abord, puis le moins travaillé
    drill = sorted(ROLES[role]["drills"][cat], key=lambda d: (mastered(d), history.get(d[0], [0, 0])[0]))[0]
    tries, ok = history.get(drill[0], [0, 0])
    return {"id": drill[0], "title": drill[1], "steps": drill[2], "category": cat, "tries": tries, "ok": ok,
            "reason": bad[0]["label"] if bad else None}


def agreement(entry):
    if len(entry["per"]) == 1:
        return "une source"
    return "sources d'accord" if entry["spread"] <= 0.03 else "sources divergentes"


def counters(mu, pool, games, enemy):
    K = 15
    picks = []
    for champ, p in pool.items():
        entry = mu["combined"].get(champ, {}).get(enemy)
        if not entry:
            continue
        mine = [x for x in games if x["champ"] == champ and x["enemy"] == enemy]
        pn, pw = len(mine), sum(1 for x in mine if x["result"] == "W")
        matchup_wr = 100 * (pw + entry["wr"] * K) / (pn + K)
        bonus = mastery_bonus(p)
        picks.append({"champ": champ, "comfort": p["comfort"], "pool_games": p["games"], "wr": 100 * entry["wr"],
                      "games": entry["games"], "per": {k: 100 * wr for k, (g, wr) in entry["per"].items()},
                      "agreement": agreement(entry), "my_games": pn, "my_wins": pw,
                      "matchup": matchup_wr, "bonus": bonus, "score": matchup_wr + bonus})
    picks.sort(key=lambda p: -p["score"])
    best = []
    for champ, opps in mu["combined"].items():
        entry = opps.get(enemy)
        if champ == enemy or champ in pool or not entry or len(entry["per"]) < 2 or entry["games"] < 200:
            continue
        worst = min(wr for _, wr in entry["per"].values())
        best.append({"champ": champ, "wr": 100 * entry["wr"], "worst": 100 * worst, "games": entry["games"],
                     "agreement": agreement(entry)})
    best.sort(key=lambda b: -b["worst"])  # classé sur la source la plus pessimiste
    return picks, best[:6]


def suggested_bans(mu, pool):
    """Adversaires contre lesquels ton pool fait le pire score, pondéré par ton aisance sur chaque champion."""
    scores = {}
    for enemy in mu["champions"]:
        num = den = 0
        for champ, p in pool.items():
            entry = mu["combined"].get(champ, {}).get(enemy)
            if champ != enemy and entry and entry["games"] >= 150:
                num += p["comfort"] * entry["wr"]
                den += p["comfort"]
        if den:
            scores[enemy] = 100 * num / den
    return sorted(scores.items(), key=lambda kv: kv[1])[:3]


def hard_matchups(games, min_games=2):
    by = {}
    for g in games:
        if g["enemy"]:
            r = by.setdefault(g["enemy"], [0, 0])
            r[0] += 1
            r[1] += 1 if g["result"] == "W" else 0
    rows = [(e, n, w) for e, (n, w) in by.items() if n >= min_games and w / n <= 0.4]
    return sorted(rows, key=lambda r: (r[2] / r[1], -r[1]))


def sparkline(values, target=None, lo=None, hi=None, w=320, h=120):
    pts = [v for v in values if v is not None]
    if len(pts) < 2:
        return ""
    lo = min(pts + ([target] if target is not None else [])) if lo is None else lo
    hi = max(pts + ([target] if target is not None else [])) if hi is None else hi
    if hi == lo:
        hi = lo + 1
    pad = 10
    x = lambda i: pad + i * (w - 2 * pad) / (len(pts) - 1)
    y = lambda v: h - pad - (min(max(v, lo), hi) - lo) / (hi - lo) * (h - 2 * pad)
    path = " ".join(f"{'M' if i == 0 else 'L'}{x(i):.1f} {y(v):.1f}" for i, v in enumerate(pts))
    svg = f'<svg viewBox="0 0 {w} {h}" class="spark" role="img">'
    if target is not None:
        svg += f'<line class="tg" x1="{pad}" x2="{w - pad}" y1="{y(target):.1f}" y2="{y(target):.1f}"/>'
    svg += f'<path class="ln" d="{path}"/>'
    svg += f'<circle class="dot" cx="{x(len(pts) - 1):.1f}" cy="{y(pts[-1]):.1f}" r="4"/></svg>'
    return svg


TIER_COLORS = ["#8A7E7A", "#B97452", "#A6B4C2", "#F0B232", "#4FB3A9", "#2DBE7A", "#7C8CFF", "#B565F0"]


def band_label(v):
    """Libellé court de la division qui commence à la valeur v : D3, E1, M, M+200…"""
    if v >= len(TIERS) * 400:
        extra = v - len(TIERS) * 400
        return "M" if extra == 0 else f"M+{extra}"
    return f"{TIERS[v // 400][0]}{4 - (v % 400) // 100}"


def lp_chart(games, name, w=1140, h=300):
    """Courbe des LP façon dpm.lol : une bande par division, couleurs de tier, un point par partie.
    games : parties chronologiques avec rang renseigné. name : fonction clé -> nom du champion."""
    from html import escape
    pts = [(rank_value(g["rank_div"], g["rank_lp"]), g) for g in games if g["rank_div"]]
    if len(pts) < 2:
        return None
    vals = [v for v, _ in pts]
    lo = max(0, (min(vals) - 25) // 100 * 100)
    hi = -(-(max(vals) + 25) // 100) * 100
    if hi - lo < 200:
        hi = lo + 200
    pl, pr, pt, pb = 40, 12, 10, 28
    x = lambda i: pl + i * (w - pl - pr) / (len(pts) - 1)
    y = lambda v: pt + (hi - v) / (hi - lo) * (h - pt - pb)
    out = [f'<svg viewBox="0 0 {w} {h}" class="lpchart" role="img" aria-label="Évolution des LP">',
           '<defs><linearGradient id="lpfill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5383E8" stop-opacity=".35"/>'
           '<stop offset="1" stop-color="#5383E8" stop-opacity="0"/></linearGradient></defs>']
    for i, b in enumerate(range(lo, hi, 100)):
        color = TIER_COLORS[min(b // 400, len(TIER_COLORS) - 1)]
        out.append(f'<rect x="{pl}" y="{y(b + 100):.1f}" width="{w - pl - pr}" height="{y(b) - y(b + 100):.1f}" fill="{color}" opacity="{0.10 if i % 2 else 0.05}"/>')
        out.append(f'<text x="{pl - 8}" y="{(y(b) + y(b + 100)) / 2 + 4:.1f}" text-anchor="end" class="ax" fill="{color}">{band_label(b)}</text>')
        out.append(f'<text x="{w - pr - 8}" y="{(y(b) + y(b + 100)) / 2 + 4:.1f}" text-anchor="end" class="ax r" fill="{color}">{band_label(b)}</text>')
    for b in range(lo, hi + 1, 100):
        tier_edge = b % 400 == 0 and b <= len(TIERS) * 400
        color = TIER_COLORS[min(b // 400, len(TIER_COLORS) - 1)]
        out.append(f'<line x1="{pl}" x2="{w - pr}" y1="{y(b):.1f}" y2="{y(b):.1f}" stroke="{color if tier_edge else "#2A3249"}" '
                   f'stroke-width="{1.5 if tier_edge else 1}" opacity="{0.8 if tier_edge else 1}"/>')
    line = " ".join(f"{'M' if i == 0 else 'L'}{x(i):.1f} {y(v):.1f}" for i, (v, _) in enumerate(pts))
    out.append(f'<path d="{line} L{x(len(pts) - 1):.1f} {h - pb} L{x(0):.1f} {h - pb} Z" fill="url(#lpfill)"/>')
    out.append(f'<path d="{line}" fill="none" stroke="#7AA0F0" stroke-width="2.5" stroke-linejoin="round"/>')
    for i, (v, g) in enumerate(pts):
        delta = f" ({g['lp_change']:+d} LP)".replace("-", "−") if g.get("lp_change") is not None else ""
        tip = (f"{g['played_on'][8:10]}/{g['played_on'][5:7]} · {name(g['champ'])}" + (f" vs {name(g['enemy'])}" if g["enemy"] else "")
               + f" · {'Victoire' if g['result'] == 'W' else 'Défaite'} · {rank_label(g['rank_div'], g['rank_lp'])}{delta}")
        out.append(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="{5 if i == len(pts) - 1 else 4}" class="pt {g["result"]}" data-tip="{escape(tip)}" tabindex="0"/>')
    step = max(1, (len(pts) - 1) // 5)
    for i in sorted({*range(0, len(pts), step), len(pts) - 1}):
        if i != len(pts) - 1 and len(pts) - 1 - i < step / 2:
            continue
        d = pts[i][1]["played_on"]
        anchor = "start" if i == 0 else "end" if i == len(pts) - 1 else "middle"
        out.append(f'<text x="{x(i):.1f}" y="{h - 8}" text-anchor="{anchor}" class="ax">{d[8:10]}/{d[5:7]}</text>')
    out.append("</svg>")
    first, last = pts[0][1], pts[-1][1]
    peak = max(pts, key=lambda p: p[0])[1]
    return {"svg": "".join(out), "net": vals[-1] - vals[0], "games": len(pts), "first": first, "last": last, "peak": peak,
            "wins": sum(1 for _, g in pts[1:] if g["result"] == "W"), "losses": sum(1 for _, g in pts[1:] if g["result"] == "L")}
