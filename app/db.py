import hashlib
import os
import secrets
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "/data/league-coach.db")
ROLES = ("top", "jungle", "mid", "adc", "support")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    pw_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    session_version INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    riot_id TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT 'euw',
    rank_div TEXT,
    rank_lp INTEGER,
    goal_div TEXT,
    role TEXT NOT NULL DEFAULT 'jungle',
    puuid TEXT,
    synced_at TEXT,
    sync_error TEXT,
    sync_added INTEGER,
    ranked_games INTEGER,
    lp_value INTEGER,
    lp_match TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS pool (
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    champ TEXT NOT NULL,
    comfort INTEGER NOT NULL,
    PRIMARY KEY (account_id, role, champ)
);
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    played_on TEXT NOT NULL,
    champ TEXT NOT NULL,
    enemy TEXT,
    result TEXT NOT NULL,
    kills INTEGER,
    deaths INTEGER,
    assists INTEGER,
    deaths_pre15 INTEGER,
    kp INTEGER,
    cs_min REAL,
    control_wards INTEGER,
    obj_lost_free INTEGER,
    focus TEXT,
    focus_ok INTEGER,
    rank_div TEXT,
    rank_lp INTEGER,
    lesson TEXT,
    match_id TEXT,
    played_at INTEGER,
    reviewed INTEGER NOT NULL DEFAULT 1,
    lp_change INTEGER,
    cs10 INTEGER,
    gd15 INTEGER,
    dmg_share INTEGER,
    role TEXT,
    vision_min REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS games_account ON games(account_id, played_on);
-- Parties Riot à ne pas importer : remake, partie supprimée par l'utilisateur ('deleted'),
-- ou ignorée par une ancienne version qui ne suivait qu'un rôle par compte ('legacy', rôles suivis dans roles)
CREATE TABLE IF NOT EXISTS skipped (
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    match_id TEXT NOT NULL,
    reason TEXT,
    roles TEXT,
    PRIMARY KEY (account_id, match_id)
);
"""


def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    old = os.path.join(os.path.dirname(DB_PATH), "jungle-coach.db")  # base de l'ancien nom du projet
    if not os.path.exists(DB_PATH) and os.path.exists(old):
        os.rename(old, DB_PATH)
    with connect() as con:
        cols = [r["name"] for r in con.execute("PRAGMA table_info(pool)")]
        if "tier" in cols:  # migration : main/secondaire/situationnel -> aisance 1 à 5
            con.executescript("""
                ALTER TABLE pool RENAME TO pool_old;
                CREATE TABLE pool (account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                                   champ TEXT NOT NULL, comfort INTEGER NOT NULL, PRIMARY KEY (account_id, champ));
                INSERT INTO pool (account_id, champ, comfort)
                    SELECT account_id, champ, CASE tier WHEN 'main' THEN 5 WHEN 'secondaire' THEN 3 ELSE 2 END FROM pool_old;
                DROP TABLE pool_old;
            """)
            cols = ["account_id", "champ", "comfort"]
        con.executescript(SCHEMA)
        # colonnes ajoutées pour la synchronisation Riot
        for table, col, decl in [("users", "session_version", "INTEGER NOT NULL DEFAULT 0"), ("accounts", "role", "TEXT NOT NULL DEFAULT 'jungle'"),
                                 ("games", "cs10", "INTEGER"), ("games", "gd15", "INTEGER"), ("games", "dmg_share", "INTEGER"), ("accounts", "puuid", "TEXT"), ("accounts", "synced_at", "TEXT"), ("accounts", "sync_error", "TEXT"),
                                 ("accounts", "sync_added", "INTEGER"), ("accounts", "ranked_games", "INTEGER"), ("accounts", "lp_value", "INTEGER"), ("accounts", "lp_match", "TEXT"), ("games", "lp_change", "INTEGER"), ("games", "match_id", "TEXT"), ("games", "played_at", "INTEGER"),
                                 ("games", "reviewed", "INTEGER NOT NULL DEFAULT 1"), ("games", "role", "TEXT"), ("games", "vision_min", "REAL"),
                                 ("skipped", "reason", "TEXT"), ("skipped", "roles", "TEXT")]:
            if col not in [r["name"] for r in con.execute(f"PRAGMA table_info({table})")]:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        if cols and "role" not in cols:   # migration : un pool par rôle (avant : un rôle par compte)
            con.executescript(f"""
                ALTER TABLE pool RENAME TO pool_old;
                CREATE TABLE pool (account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE, role TEXT NOT NULL,
                                   champ TEXT NOT NULL, comfort INTEGER NOT NULL, PRIMARY KEY (account_id, role, champ));
                INSERT OR IGNORE INTO pool (account_id, role, champ, comfort)
                    SELECT p.account_id, {ACCOUNT_ROLE}, p.champ, p.comfort FROM pool_old p JOIN accounts a ON a.id = p.account_id;
                DROP TABLE pool_old;
            """)
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS games_match ON games(account_id, match_id) WHERE match_id IS NOT NULL")
        migrate_roles(con)


ACCOUNT_ROLE = f"CASE WHEN a.role IN {ROLES} THEN a.role ELSE 'jungle' END"


def migrate_roles(con):
    """Passage d'un rôle par compte à tous les rôles par compte (idempotent).
    - chaque partie existante prend le rôle que suivait son compte ;
    - les parties Riot ignorées par l'ancienne version sont marquées 'legacy' : la synchronisation suivante
      les relit et importe celles jouées sur un autre rôle (une partie du rôle suivi y était forcément
      parce que l'utilisateur l'avait supprimée : elle reste ignorée) ;
    - les comptes ajoutés en double pour suivre deux rôles (même Riot ID) sont fusionnés."""
    con.execute(f"UPDATE games SET role = (SELECT {ACCOUNT_ROLE} FROM accounts a WHERE a.id = games.account_id) WHERE role IS NULL")
    con.execute(f"""UPDATE skipped SET reason = 'legacy', roles = (SELECT {ACCOUNT_ROLE} FROM accounts a WHERE a.id = skipped.account_id)
                    WHERE reason IS NULL""")
    groups = con.execute("""SELECT user_id, lower(trim(riot_id)) AS rid, region, group_concat(id) AS ids FROM accounts
                            GROUP BY user_id, rid, region HAVING COUNT(*) > 1""").fetchall()
    for g in groups:
        ids = sorted(int(i) for i in g["ids"].split(","))
        keep = ids[0]
        latest = con.execute(f"SELECT * FROM accounts WHERE id IN ({','.join('?' * len(ids))}) ORDER BY COALESCE(synced_at, '') DESC, id LIMIT 1", ids).fetchone()
        for dup in ids[1:]:
            # parties : déplacées sauf doublon exact d'une partie Riot déjà présente
            con.execute("""UPDATE games SET account_id = ? WHERE account_id = ? AND (match_id IS NULL OR match_id NOT IN
                           (SELECT match_id FROM games WHERE account_id = ? AND match_id IS NOT NULL))""", (keep, dup, keep))
            con.execute("INSERT OR IGNORE INTO pool (account_id, role, champ, comfort) SELECT ?, role, champ, comfort FROM pool WHERE account_id = ?", (keep, dup))
            for s in con.execute("SELECT * FROM skipped WHERE account_id = ?", (dup,)).fetchall():
                mine = con.execute("SELECT * FROM skipped WHERE account_id = ? AND match_id = ?", (keep, s["match_id"])).fetchone()
                if not mine:
                    con.execute("INSERT INTO skipped (account_id, match_id, reason, roles) VALUES (?, ?, ?, ?)", (keep, s["match_id"], s["reason"], s["roles"]))
                elif mine["reason"] == "legacy" and s["reason"] == "legacy":
                    roles = ",".join(sorted(set((mine["roles"] or "").split(",")) | set((s["roles"] or "").split(",")) - {""}))
                    con.execute("UPDATE skipped SET roles = ? WHERE account_id = ? AND match_id = ?", (roles, keep, s["match_id"]))
                elif s["reason"] == "deleted":
                    con.execute("UPDATE skipped SET reason = 'deleted' WHERE account_id = ? AND match_id = ?", (keep, s["match_id"]))
            con.execute("DELETE FROM accounts WHERE id = ?", (dup,))
        # une partie importée par l'un des comptes n'est plus « ignorée » pour le compte fusionné
        con.execute("DELETE FROM skipped WHERE account_id = ? AND match_id IN (SELECT match_id FROM games WHERE account_id = ? AND match_id IS NOT NULL)", (keep, keep))
        con.execute("""UPDATE accounts SET puuid = COALESCE(puuid, ?), rank_div = ?, rank_lp = ?, ranked_games = ?, lp_value = ?, lp_match = ?,
                       goal_div = COALESCE(goal_div, ?) WHERE id = ?""",
                    (latest["puuid"], latest["rank_div"], latest["rank_lp"], latest["ranked_games"], latest["lp_value"], latest["lp_match"],
                     latest["goal_div"], keep))


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1).hex()
    return f"{salt}${digest}"


def check_password(password, stored):
    salt, digest = stored.split("$")
    test = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1).hex()
    return secrets.compare_digest(test, digest)
