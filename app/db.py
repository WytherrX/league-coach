import hashlib
import os
import secrets
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "/data/league-coach.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    pw_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
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
    champ TEXT NOT NULL,
    comfort INTEGER NOT NULL,
    PRIMARY KEY (account_id, champ)
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
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS games_account ON games(account_id, played_on);
CREATE TABLE IF NOT EXISTS skipped (
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    match_id TEXT NOT NULL,
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
        con.executescript(SCHEMA)
        # colonnes ajoutées pour la synchronisation Riot
        for table, col, decl in [("accounts", "puuid", "TEXT"), ("accounts", "synced_at", "TEXT"), ("accounts", "sync_error", "TEXT"),
                                 ("accounts", "sync_added", "INTEGER"), ("accounts", "ranked_games", "INTEGER"), ("accounts", "lp_value", "INTEGER"), ("accounts", "lp_match", "TEXT"), ("games", "lp_change", "INTEGER"), ("games", "match_id", "TEXT"), ("games", "played_at", "INTEGER"),
                                 ("games", "reviewed", "INTEGER NOT NULL DEFAULT 1")]:
            if col not in [r["name"] for r in con.execute(f"PRAGMA table_info({table})")]:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS games_match ON games(account_id, match_id) WHERE match_id IS NOT NULL")


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1).hex()
    return f"{salt}${digest}"


def check_password(password, stored):
    salt, digest = stored.split("$")
    test = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1).hex()
    return secrets.compare_digest(test, digest)
