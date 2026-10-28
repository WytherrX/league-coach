"""Synchronisation des parties classées solo/duo depuis l'API Riot, en tâche de fond."""
import logging
import os
import threading
import time

import analysis
import db
import riot

FIRST_IMPORT = 50                      # parties classées lues lors de la première synchronisation
INTERVAL = max(5, int(os.environ.get("SYNC_MINUTES", "10")))
LOCK = threading.Lock()                # une seule synchronisation à la fois (limites de débit de la clé)
RUNNING = set()                        # comptes en cours de synchronisation, pour l'interface
log = logging.getLogger("uvicorn.error")

STAT_COLS = ["played_on", "played_at", "champ", "enemy", "result", "kills", "deaths", "assists",
             "deaths_pre15", "kp", "cs_min", "control_wards", "obj_lost_free", "cs10", "gd15", "dmg_share", "vision_min", "role"]


def save_game(con, account_id, g):
    """Ajoute une partie importée. Si tu l'avais déjà saisie à la main (même jour, champion, résultat et KDA),
    la ligne existante est complétée : ton objectif et ta leçon sont conservés."""
    manual = con.execute("""SELECT id FROM games WHERE account_id = ? AND match_id IS NULL AND played_on = ? AND champ = ?
                            AND result = ? AND (kills IS NULL OR kills = ?) AND (deaths IS NULL OR deaths = ?)
                            AND (assists IS NULL OR assists = ?) ORDER BY id LIMIT 1""",
                         (account_id, g["played_on"], g["champ"], g["result"], g["kills"], g["deaths"], g["assists"])).fetchone()
    if manual:
        sets = ", ".join(f"{c} = ?" for c in STAT_COLS)
        con.execute(f"UPDATE games SET {sets}, match_id = ? WHERE id = ?", [g[c] for c in STAT_COLS] + [g["match_id"], manual["id"]])
        return manual["id"]
    cols = ["account_id", "match_id", "reviewed"] + STAT_COLS
    cur = con.execute(f"INSERT INTO games ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                      [account_id, g["match_id"], 0] + [g[c] for c in STAT_COLS])
    return cur.lastrowid


def record_lp(con, acc, newest, div, lp, total):
    """Relevé de LP après la dernière partie classée.
    Le classement (League-V4) et l'historique (Match-V5) ne se mettent pas à jour au même moment :
    on n'avance le relevé que lorsque les deux montrent la même nouvelle partie."""
    value = analysis.rank_value(div, lp)
    if acc["ranked_games"] is not None and total == acc["ranked_games"]:
        con.execute("UPDATE accounts SET lp_value = ? WHERE id = ?", (value, acc["id"]))   # pas de partie : ajustement ou decay
        return
    if acc["ranked_games"] is not None and newest == acc["lp_match"]:
        return   # le classement a bougé mais la partie n'est pas encore dans l'historique : prochaine synchro
    game = con.execute("SELECT id FROM games WHERE account_id = ? AND match_id = ?", (acc["id"], newest or "")).fetchone()
    if game:
        con.execute("UPDATE games SET rank_div = ?, rank_lp = ? WHERE id = ?", (div, lp, game["id"]))
        # Écart de LP attribuable seulement si une seule partie classée a été jouée depuis le relevé précédent
        if acc["ranked_games"] is not None and acc["lp_value"] is not None and total - acc["ranked_games"] == 1:
            con.execute("UPDATE games SET lp_change = ? WHERE id = ?", (value - acc["lp_value"], game["id"]))
    con.execute("UPDATE accounts SET ranked_games = ?, lp_value = ?, lp_match = ? WHERE id = ?", (total, value, newest, acc["id"]))


def sync_account(account_id):
    with db.connect() as con:
        acc = con.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if not acc:
        return 0
    RUNNING.add(account_id)
    added = 0
    try:
        pid = acc["puuid"] or riot.puuid(acc["riot_id"], acc["region"])
        with db.connect() as con:
            con.execute("UPDATE accounts SET puuid = ? WHERE id = ?", (pid, account_id))
            known = {r[0] for r in con.execute("""SELECT match_id FROM games WHERE account_id = ? AND match_id IS NOT NULL
                                                  UNION SELECT match_id FROM skipped WHERE account_id = ? AND reason IS NOT 'legacy'""",
                                               (account_id, account_id))}
            # parties ignorées par l'ancienne version (un seul rôle suivi) : relues une fois
            legacy = {r[0]: set((r[1] or "").split(",")) for r in con.execute(
                "SELECT match_id, roles FROM skipped WHERE account_id = ? AND reason = 'legacy'", (account_id,))}
        ids = riot.match_ids(pid, acc["region"], FIRST_IMPORT if acc["synced_at"] is None or legacy else 20)
        for mid in reversed([m for m in ids if m not in known]):   # du plus ancien au plus récent
            m, timeline = riot.match(mid, acc["region"])
            if not m:
                continue
            game, reason = riot.parse_game(m, timeline, pid)
            with db.connect() as con:
                if mid in legacy:
                    if game and game["role"] not in legacy[mid]:     # jouée sur un autre rôle : on l'importe enfin
                        con.execute("DELETE FROM skipped WHERE account_id = ? AND match_id = ?", (account_id, mid))
                        save_game(con, account_id, game)
                        added += 1
                    else:   # remake, ou partie du rôle suivi que l'utilisateur avait supprimée
                        con.execute("UPDATE skipped SET reason = ? WHERE account_id = ? AND match_id = ?",
                                    (reason or "deleted", account_id, mid))
                elif game:
                    save_game(con, account_id, game)
                    added += 1
                else:   # remake : on ne la relit plus
                    con.execute("INSERT OR IGNORE INTO skipped (account_id, match_id, reason) VALUES (?, ?, ?)", (account_id, mid, reason))
        if legacy:   # plus anciennes que la fenêtre relue : elles ne reviendront plus dans l'historique
            with db.connect() as con:
                con.execute("UPDATE skipped SET reason = 'old' WHERE account_id = ? AND reason = 'legacy'", (account_id,))
        div, lp, total = riot.solo_rank(pid, acc["region"])
        with db.connect() as con:
            if div:
                con.execute("UPDATE accounts SET rank_div = ?, rank_lp = ? WHERE id = ?", (div, lp, account_id))
                record_lp(con, acc, ids[0] if ids else None, div, lp, total)
            con.execute("UPDATE accounts SET synced_at = datetime('now'), sync_error = NULL, sync_added = ? WHERE id = ?",
                        (added, account_id))
    except riot.RiotError as e:
        with db.connect() as con:
            con.execute("UPDATE accounts SET sync_error = ? WHERE id = ?", (str(e), account_id))
        log.warning("Synchro Riot du compte %s : %s", acc["riot_id"], e)
    except Exception:
        log.exception("Synchro Riot du compte %s", acc["riot_id"])
        with db.connect() as con:
            con.execute("UPDATE accounts SET sync_error = ? WHERE id = ?", ("Erreur inattendue, voir les logs du conteneur", account_id))
    finally:
        RUNNING.discard(account_id)
    return added


def run(account_ids=None):
    if not LOCK.acquire(blocking=False):
        return False
    try:
        if account_ids is None:
            with db.connect() as con:
                account_ids = [r[0] for r in con.execute("SELECT id FROM accounts ORDER BY id")]
        for aid in account_ids:
            sync_account(aid)
    finally:
        LOCK.release()
    return True


def trigger(account_id):
    """Synchronisation à la demande, sans bloquer la page."""
    if LOCK.locked():
        return False
    RUNNING.add(account_id)
    threading.Thread(target=run, args=([account_id],), daemon=True).start()
    return True


def _loop():
    time.sleep(5)
    while True:
        run()
        time.sleep(INTERVAL * 60)


def start():
    if riot.API_KEY:
        threading.Thread(target=_loop, daemon=True).start()
        log.info("Synchronisation Riot active, toutes les %s minutes", INTERVAL)
    else:
        log.warning("RIOT_API_KEY absente du .env : import automatique des parties désactivé")
