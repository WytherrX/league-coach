import datetime
import hashlib
import json
import logging
import math
import os
import secrets
import time
import urllib.parse

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import analysis
import db
import riot
import sync

SECRET_KEY = os.environ.get("SECRET_KEY", "")
ALLOW_SIGNUP = os.environ.get("ALLOW_SIGNUP", "false").lower() == "true"
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
if len(SECRET_KEY) < 32:
    raise SystemExit("SECRET_KEY doit faire au moins 32 caractères (voir .env.example)")

HERE = os.path.dirname(__file__)
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, https_only=COOKIE_SECURE,
                   same_site="lax", max_age=30 * 24 * 3600, session_cookie="lc_session")
app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(HERE, "templates"))

db.init()
MU = analysis.load_matchups()
sync.start()
log = logging.getLogger("uvicorn.error")


# ---------- Sécurité des requêtes ----------

SECURITY_HEADERS = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data: https://ddragon.leagueoflegends.com; "
                               "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
                               "script-src 'self' 'unsafe-inline'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'; object-src 'none'",
}


def same_origin(request):
    """Protection CSRF : un formulaire envoyé par un navigateur porte l'en-tête Origin (ou Referer).
    Il doit venir du même nom d'hôte que l'appli. Sans ces en-têtes, ce n'est pas un navigateur : pas de CSRF possible."""
    source = request.headers.get("origin") or request.headers.get("referer")
    if not source:
        return True
    host = urllib.parse.urlsplit("//" + request.headers.get("host", "")).hostname
    return urllib.parse.urlsplit(source).hostname == host and host is not None


@app.middleware("http")
async def security(request: Request, call_next):
    if request.method not in ("GET", "HEAD", "OPTIONS") and not same_origin(request):
        return PlainTextResponse("Requête refusée : elle ne vient pas de League Coach.", status_code=403)
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


def safe_next(url, default):
    """Redirection après un formulaire : uniquement vers une page de l'appli (pas //site.com ni /\\site.com)."""
    return url if url.startswith("/") and not url.startswith(("//", "/\\")) else default


# ---------- Limite des tentatives de connexion ----------

FAILS = {}                       # "u:identifiant" ou "ip:adresse" -> horodatages des échecs
FAIL_WINDOW = 15 * 60
FAIL_LIMITS = {"u": 10, "ip": 30}


def blocked(key):
    now = time.monotonic()
    recent = [t for t in FAILS.get(key, []) if now - t < FAIL_WINDOW]
    if recent:
        FAILS[key] = recent
    else:
        FAILS.pop(key, None)
    return len(recent) >= FAIL_LIMITS[key.split(":")[0]]


def record_fail(*keys):
    if len(FAILS) > 50_000:      # garde-fou mémoire si quelqu'un essaie des milliers d'identifiants
        FAILS.clear()
    for key in keys:
        FAILS.setdefault(key, []).append(time.monotonic())


# Hachage factice : une connexion avec un identifiant inconnu prend autant de temps qu'avec un vrai
DUMMY_HASH = db.hash_password(secrets.token_hex(16))
PASSWORD_MAX = 128


# ---------- Code d'installation du premier compte ----------

SETUP_CODE = None


def no_users():
    with db.connect() as con:
        return con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


if no_users():
    SETUP_CODE = f"{secrets.randbelow(10**6):06d}-{secrets.randbelow(10**6):06d}"
    log.warning("Aucun compte : code d'installation pour créer le compte administrateur : %s", SETUP_CODE)


def champ_name(key):
    return MU["champions"].get(key, {}).get("name", key or "—")


def champ_icon(key):
    img = MU["champions"].get(key, {}).get("img")
    return f"https://ddragon.leagueoflegends.com/cdn/{MU['ddragon']}/img/champion/{img}.png" if img else ""


TIER_CLASS = {"I": "iron", "B": "bronze", "S": "silver", "G": "gold", "P": "plat", "E": "emerald", "D": "diamond",
              "M": "master", "GM": "gm", "C": "chall"}


def tier_class(div):
    if not div:
        return "t-unranked"
    return "t-" + TIER_CLASS.get(div if div in ("M", "GM", "C") else div[0], "unranked")


def wr_class(v):
    if v is None:
        return ""
    return "wr-great" if v >= 55 else "wr-good" if v >= 52 else "wr-ok" if v >= 48 else "wr-bad"


def kda(k, d, a):
    """Ratio KDA et classe de couleur, façon op.gg."""
    if None in (k, d, a):
        return None, ""
    r = (k + a) / max(d, 1)
    return r, "kda-great" if r >= 5 else "kda-good" if r >= 4 else "kda-ok" if r >= 3 else "kda-low"


def ago(ts):
    """'2026-10-26 12:40:00' (UTC, format SQLite) -> 'il y a 5 min'."""
    if not ts:
        return "jamais"
    s = (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(ts).replace(tzinfo=datetime.timezone.utc)).total_seconds()
    if s < 60:
        return "à l'instant"
    if s < 3600:
        return f"il y a {int(s // 60)} min"
    if s < 86400:
        return f"il y a {int(s // 3600)} h"
    return f"il y a {int(s // 86400)} j"


templates.env.filters["ago"] = ago
templates.env.filters["pts"] = lambda b: "0" if b == 0 else f"{b:+g}".replace(".", ",").replace("-", "−") + (" pt" if abs(b) < 2 else " pts")
templates.env.filters["fr"] = lambda v, d=1: f"{v:.{d}f}".replace(".", ",")
# Version du CSS dans l'URL : un navigateur ou un proxy ne peut pas garder une ancienne feuille de style en cache
with open(os.path.join(HERE, "static", "style.css"), "rb") as f:
    STATIC_V = hashlib.sha1(f.read()).hexdigest()[:10]
templates.env.globals.update(STATIC_V=STATIC_V, COMFORT=analysis.COMFORT, mastery_bonus=analysis.mastery_bonus, champ_name=champ_name, champ_icon=champ_icon, rank_label=analysis.rank_label,
                             RANKS=analysis.RANKS, DRILLS=analysis.DRILLS, DRILL_INDEX=analysis.DRILL_INDEX,
                             tier_class=tier_class, wr_class=wr_class, kda=kda, RIOT=bool(riot.API_KEY), SYNC_MINUTES=sync.INTERVAL)


def go(url):
    return RedirectResponse(url, status_code=303)


def current_user(request):
    uid = request.session.get("uid")
    if not uid:
        return None
    with db.connect() as con:
        user = con.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    # Session révoquée (mot de passe changé, « déconnecter mes autres appareils ») ou utilisateur supprimé
    if not user or request.session.get("sv", 0) != user["session_version"]:
        request.session.clear()
        return None
    return user


def start_session(request, user):
    request.session.clear()
    request.session["uid"] = user["id"]
    request.session["sv"] = user["session_version"]


def user_accounts(user):
    with db.connect() as con:
        return con.execute("SELECT * FROM accounts WHERE user_id = ? ORDER BY id", (user["id"],)).fetchall()


def active_account(request, user):
    accounts = user_accounts(user)
    if not accounts:
        return None, accounts
    wanted = request.session.get("account")
    acc = next((a for a in accounts if a["id"] == wanted), accounts[0])
    request.session["account"] = acc["id"]
    return acc, accounts


def get_pool(account_id):
    with db.connect() as con:
        rows = con.execute("""SELECT p.champ, p.comfort, COUNT(g.id) AS games, COALESCE(SUM(g.result = 'W'), 0) AS wins
                              FROM pool p LEFT JOIN games g ON g.account_id = p.account_id AND g.champ = p.champ
                              WHERE p.account_id = ? GROUP BY p.champ, p.comfort
                              ORDER BY p.comfort DESC, games DESC""", (account_id,)).fetchall()
    return {r["champ"]: {"comfort": r["comfort"], "games": r["games"], "wins": r["wins"]} for r in rows}


def get_games(account_id, limit=None):
    sql = "SELECT * FROM games WHERE account_id = ? ORDER BY played_on DESC, COALESCE(played_at, 0) DESC, id DESC"
    with db.connect() as con:
        rows = con.execute(sql + (f" LIMIT {int(limit)}" if limit else ""), (account_id,)).fetchall()
    return [dict(r) for r in rows]


def render(request, name, user, **ctx):
    acc, accounts = active_account(request, user) if user else (None, [])
    to_review = 0
    if acc:
        with db.connect() as con:
            to_review = con.execute("SELECT COUNT(*) FROM games WHERE account_id = ? AND reviewed = 0", (acc["id"],)).fetchone()[0]
    ctx.update(request=request, user=user, account=acc, accounts=accounts, mu=MU, flash=request.session.pop("flash", None),
               to_review=to_review, syncing=bool(acc and acc["id"] in sync.RUNNING),
               all_champs=sorted(MU["champions"], key=champ_name))
    return templates.TemplateResponse(request, name, ctx)


def flash(request, text, kind="ok"):
    request.session["flash"] = {"text": text, "kind": kind}


def to_int(v, lo=0, hi=100_000):
    if v in (None, ""):
        return None
    n = int(v)
    if not lo <= n <= hi:
        raise ValueError(v)
    return n


def to_float(v, lo=0, hi=100):
    if v in (None, ""):
        return None
    f = float(str(v).replace(",", "."))
    if not math.isfinite(f) or not lo <= f <= hi:
        raise ValueError(v)
    return f


def rank_or_none(v):
    return v if v in analysis.RANKS else None


# ---------- Authentification ----------

def signup_open():
    return ALLOW_SIGNUP or no_users()


def password_error(password, password2):
    if not 10 <= len(password) <= PASSWORD_MAX:
        return f"Le mot de passe doit faire entre 10 et {PASSWORD_MAX} caractères."
    if password != password2:
        return "Les deux mots de passe ne correspondent pas."
    return None


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"signup": signup_open(), "error": None})


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    username = username.strip().lower()[:64]
    keys = ("u:" + username, "ip:" + (request.client.host if request.client else "?"))
    if any(blocked(k) for k in keys):
        return templates.TemplateResponse(request, "login.html", {"signup": signup_open(),
                                          "error": "Trop de tentatives échouées. Réessaie dans 15 minutes."}, status_code=429)
    with db.connect() as con:
        user = con.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    ok = len(password) <= PASSWORD_MAX and db.check_password(password, user["pw_hash"] if user else DUMMY_HASH) and user is not None
    if not ok:
        record_fail(*keys)
        log.warning("Échec de connexion pour « %s » depuis %s", username, keys[1][3:])
        return templates.TemplateResponse(request, "login.html", {"signup": signup_open(), "error": "Identifiant ou mot de passe incorrect."}, status_code=400)
    FAILS.pop(keys[0], None)
    start_session(request, user)
    return go("/")


@app.get("/register")
def register_page(request: Request):
    if not signup_open():
        return go("/login")
    return templates.TemplateResponse(request, "register.html", {"error": None, "first": no_users()})


@app.post("/register")
def register(request: Request, username: str = Form(...), password: str = Form(...), password2: str = Form(...),
             setup_code: str = Form("")):
    global SETUP_CODE
    if not signup_open():
        return go("/login")
    first = no_users()
    username = username.strip().lower()
    error = None
    if first and not (SETUP_CODE and secrets.compare_digest(setup_code.strip(), SETUP_CODE)):
        error = "Code d'installation incorrect. Il s'affiche dans les journaux du conteneur : docker compose logs | grep installation"
    elif not (3 <= len(username) <= 32) or not username.replace("_", "").replace("-", "").isalnum():
        error = "L'identifiant doit faire 3 à 32 caractères : lettres, chiffres, - ou _."
    else:
        error = password_error(password, password2)
    if error:
        return templates.TemplateResponse(request, "register.html", {"error": error, "first": first}, status_code=400)
    with db.connect() as con:
        if con.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            return templates.TemplateResponse(request, "register.html", {"error": "Cet identifiant est déjà pris.", "first": first}, status_code=400)
        cur = con.execute("INSERT INTO users (username, pw_hash, is_admin) VALUES (?, ?, ?)",
                          (username, db.hash_password(password), 1 if first else 0))
        user = con.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    if first:
        SETUP_CODE = None
    start_session(request, user)
    return go("/accounts")


@app.post("/password")
def password_change(request: Request, current: str = Form(...), password: str = Form(...), password2: str = Form(...)):
    user = current_user(request)
    if not user:
        return go("/login")
    if len(current) > PASSWORD_MAX or not db.check_password(current, user["pw_hash"]):
        flash(request, "Mot de passe actuel incorrect.", "err")
        return go("/accounts#securite")
    error = password_error(password, password2)
    if error:
        flash(request, error, "err")
        return go("/accounts#securite")
    with db.connect() as con:
        con.execute("UPDATE users SET pw_hash = ?, session_version = session_version + 1 WHERE id = ?",
                    (db.hash_password(password), user["id"]))
        user = con.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
    start_session(request, user)
    flash(request, "Mot de passe changé. Tes autres appareils ont été déconnectés.")
    return go("/accounts#securite")


@app.post("/sessions/revoke")
def sessions_revoke(request: Request):
    user = current_user(request)
    if not user:
        return go("/login")
    with db.connect() as con:
        con.execute("UPDATE users SET session_version = session_version + 1 WHERE id = ?", (user["id"],))
        user = con.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
    start_session(request, user)
    flash(request, "Tes autres appareils ont été déconnectés.")
    return go("/accounts#securite")


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return go("/login")


# ---------- Tableau de bord ----------

@app.get("/")
def dashboard(request: Request, n: int = 20):
    user = current_user(request)
    if not user:
        return go("/login")
    acc, _ = active_account(request, user)
    if not acc:
        return go("/accounts")
    n = n if n in (10, 20, 50) else 20
    pool = get_pool(acc["id"])
    all_games = get_games(acc["id"])
    recent = all_games[:n]
    metrics = analysis.compute_metrics(recent, pool)
    weak = analysis.weaknesses(metrics)
    focus = analysis.next_focus(weak, all_games)
    chrono = list(reversed(all_games[:30]))
    charts = {
        "kp": analysis.sparkline([g["kp"] for g in chrono], 60, 20, 90),
        "deaths": analysis.sparkline([g["deaths"] for g in chrono], 4.5, 0, 12),
    }
    drills = {}
    for g in all_games:
        if g["focus"]:
            d = drills.setdefault(g["focus"], [0, 0])
            d[0] += 1
            d[1] += 1 if g["focus_ok"] else 0
    # Champions joués sur la période, comme le panneau « champions » d'op.gg
    by = {}
    for g in recent:
        s = by.setdefault(g["champ"], {"champ": g["champ"], "n": 0, "w": 0, "k": 0, "d": 0, "a": 0, "kn": 0})
        s["n"] += 1
        s["w"] += g["result"] == "W"
        if None not in (g["kills"], g["deaths"], g["assists"]):
            s["k"] += g["kills"]; s["d"] += g["deaths"]; s["a"] += g["assists"]; s["kn"] += 1
    champ_stats = sorted(by.values(), key=lambda s: (-s["n"], -s["w"]))[:7]
    totals = {"k": sum(s["k"] for s in by.values()), "d": sum(s["d"] for s in by.values()),
              "a": sum(s["a"] for s in by.values()), "kn": sum(s["kn"] for s in by.values())}
    streak = 0
    for g in recent:
        if g["result"] != recent[0]["result"]:
            break
        streak += 1
    wins = sum(1 for g in recent if g["result"] == "W")
    main_champ = champ_stats[0]["champ"] if champ_stats else (next(iter(pool)) if pool else None)
    lp = analysis.lp_chart([g for g in reversed(all_games) if g["rank_div"]][-60:], champ_name)
    return render(request, "dashboard.html", user, n=n, pool=pool, lp=lp, games=recent[:8], metrics=metrics, weak=weak,
                  focus=focus, charts=charts, drills=drills, hard=analysis.hard_matchups(all_games),
                  champ_stats=champ_stats, totals=totals, wins=wins, main_champ=main_champ,
                  streak=(streak, recent[0]["result"]) if recent else None,
                  bans=analysis.suggested_bans(MU, pool) if pool else [], early=analysis.EARLY)


# ---------- Comptes LoL ----------

@app.get("/accounts")
def accounts_page(request: Request):
    user = current_user(request)
    if not user:
        return go("/login")
    return render(request, "accounts.html", user)


@app.post("/accounts")
def account_add(request: Request, riot_id: str = Form(...), region: str = Form("euw"), rank_div: str = Form(""),
                rank_lp: str = Form(""), goal_div: str = Form("")):
    user = current_user(request)
    if not user:
        return go("/login")
    riot_id = riot_id.strip()
    name, _, tag = riot_id.partition("#")
    if not (1 <= len(name.strip()) <= 32 and 1 <= len(tag.strip()) <= 10) or "#" in tag:
        flash(request, "Indique ton Riot ID complet, avec le # et le tag.", "err")
        return go("/accounts")
    try:
        lp = to_int(rank_lp, 0, 5000)
    except ValueError:
        flash(request, "Les LP doivent être un nombre entre 0 et 5000.", "err")
        return go("/accounts")
    with db.connect() as con:
        cur = con.execute("INSERT INTO accounts (user_id, riot_id, region, rank_div, rank_lp, goal_div) VALUES (?, ?, ?, ?, ?, ?)",
                          (user["id"], riot_id, region if region in riot.ROUTING else "euw", rank_or_none(rank_div), lp, rank_or_none(goal_div)))
    request.session["account"] = cur.lastrowid
    if riot.API_KEY:
        sync.trigger(cur.lastrowid)
        flash(request, f"Compte {riot_id} ajouté : import de tes dernières parties classées en cours. Choisis ton champion pool en attendant.")
    else:
        flash(request, f"Compte {riot_id} ajouté. Choisis maintenant ton champion pool.")
    return go("/pool")


@app.post("/accounts/{account_id}/edit")
def account_edit(request: Request, account_id: int, rank_div: str = Form(""), rank_lp: str = Form(""), goal_div: str = Form("")):
    user = current_user(request)
    if not user:
        return go("/login")
    try:
        lp = to_int(rank_lp, 0, 5000)
    except ValueError:
        flash(request, "Les LP doivent être un nombre entre 0 et 5000.", "err")
        return go("/accounts")
    with db.connect() as con:
        con.execute("UPDATE accounts SET rank_div = ?, rank_lp = ?, goal_div = ? WHERE id = ? AND user_id = ?",
                    (rank_or_none(rank_div), lp, rank_or_none(goal_div), account_id, user["id"]))
    flash(request, "Compte mis à jour.")
    return go("/accounts")


@app.post("/accounts/{account_id}/select")
def account_select(request: Request, account_id: int, next: str = Form("/")):
    user = current_user(request)
    if not user:
        return go("/login")
    if any(a["id"] == account_id for a in user_accounts(user)):
        request.session["account"] = account_id
    return go(safe_next(next, "/"))


@app.post("/accounts/{account_id}/sync")
def account_sync(request: Request, account_id: int, next: str = Form("/games")):
    user = current_user(request)
    if not user:
        return go("/login")
    if riot.API_KEY and any(a["id"] == account_id for a in user_accounts(user)):
        if sync.trigger(account_id):
            flash(request, "Synchronisation lancée : la page se met à jour toute seule.")
        else:
            flash(request, "Une synchronisation est déjà en cours.", "err")
    return go(safe_next(next, "/games"))


@app.post("/accounts/{account_id}/delete")
def account_delete(request: Request, account_id: int, confirm: str = Form("")):
    user = current_user(request)
    if not user:
        return go("/login")
    if confirm != "SUPPRIMER":
        flash(request, "Tape SUPPRIMER pour confirmer la suppression du compte et de ses parties.", "err")
        return go("/accounts")
    with db.connect() as con:
        con.execute("DELETE FROM accounts WHERE id = ? AND user_id = ?", (account_id, user["id"]))
    request.session.pop("account", None)
    flash(request, "Compte supprimé.")
    return go("/accounts")


# ---------- Champion pool ----------

@app.get("/pool")
def pool_page(request: Request):
    user = current_user(request)
    if not user:
        return go("/login")
    acc, _ = active_account(request, user)
    if not acc:
        return go("/accounts")
    champs = sorted(MU["champions"], key=lambda k: champ_name(k))
    stats = MU["totals"]
    return render(request, "pool.html", user, pool=get_pool(acc["id"]), champs=champs, stats=stats)


@app.post("/pool")
async def pool_save(request: Request):
    user = current_user(request)
    if not user:
        return go("/login")
    acc, _ = active_account(request, user)
    if not acc:
        return go("/accounts")
    form = await request.form()
    rows = []
    for champ in MU["champions"]:
        comfort = form.get("c_" + champ, "")
        if comfort in ("1", "2", "3", "4", "5"):
            rows.append((acc["id"], champ, int(comfort)))
    with db.connect() as con:
        con.execute("DELETE FROM pool WHERE account_id = ?", (acc["id"],))
        con.executemany("INSERT INTO pool (account_id, champ, comfort) VALUES (?, ?, ?)", rows)
    flash(request, f"Pool enregistré : {len(rows)} champion{'s' if len(rows) > 1 else ''}.")
    return go("/pool")


# ---------- Parties ----------

@app.get("/games")
def games_page(request: Request):
    user = current_user(request)
    if not user:
        return go("/login")
    acc, _ = active_account(request, user)
    if not acc:
        return go("/accounts")
    pool = get_pool(acc["id"])
    all_games = get_games(acc["id"])
    weak = analysis.weaknesses(analysis.compute_metrics(all_games[:20], pool))
    focus = analysis.next_focus(weak, all_games)
    champs = sorted(MU["champions"], key=lambda k: champ_name(k))
    pool_sorted = list(pool)  # déjà trié par aisance puis nombre de parties
    return render(request, "games.html", user, games=all_games, focus=focus, champs=champs, pool_sorted=pool_sorted,
                  today=datetime.date.today().isoformat())


@app.post("/games")
def game_add(request: Request, played_on: str = Form(...), champ: str = Form(...), enemy: str = Form(""),
             result: str = Form(...), kills: str = Form(""), deaths: str = Form(""), assists: str = Form(""),
             deaths_pre15: str = Form(""), kp: str = Form(""), cs_min: str = Form(""), control_wards: str = Form(""),
             obj_lost_free: str = Form(""), focus: str = Form(""), focus_ok: str = Form(""), rank_div: str = Form(""),
             rank_lp: str = Form(""), lesson: str = Form("")):
    user = current_user(request)
    if not user:
        return go("/login")
    acc, _ = active_account(request, user)
    if not acc:
        return go("/accounts")
    if champ not in MU["champions"] or (enemy and enemy not in MU["champions"]):
        flash(request, "Choisis les champions dans la liste.", "err")
        return go("/games")
    try:
        datetime.date.fromisoformat(played_on)
        values = (acc["id"], played_on, champ, enemy or None,
                  "W" if result == "W" else "L", to_int(kills, 0, 100), to_int(deaths, 0, 100), to_int(assists, 0, 100),
                  to_int(deaths_pre15, 0, 100), to_int(kp, 0, 100), to_float(cs_min, 0, 20), to_int(control_wards, 0, 100),
                  to_int(obj_lost_free, 0, 50),
                  focus if focus in analysis.DRILL_INDEX else None, None if focus_ok == "" else int(focus_ok == "1"),
                  rank_or_none(rank_div), to_int(rank_lp, 0, 5000), lesson.strip()[:500] or None)
    except ValueError:
        flash(request, "Une valeur n'est pas valide (nombre ou date). Vérifie le formulaire.", "err")
        return go("/games")
    with db.connect() as con:
        # Partie déjà importée depuis Riot (même jour, champion, résultat et KDA) : on la complète au lieu de la dupliquer
        imported = con.execute("""SELECT id FROM games WHERE account_id = ? AND match_id IS NOT NULL AND played_on = ? AND champ = ?
                                  AND result = ? AND kills IS ? AND deaths IS ? AND assists IS ? LIMIT 1""",
                               (acc["id"], values[1], values[2], values[4], values[5], values[6], values[7])).fetchone()
        if imported:
            con.execute("UPDATE games SET focus = ?, focus_ok = ?, lesson = ?, reviewed = 1 WHERE id = ?",
                        (values[13], values[14], values[17], imported["id"]))
            flash(request, "Cette partie était déjà importée depuis Riot : objectif et leçon ajoutés.")
            return go("/games")
        # LP gagnés ou perdus : écart avec le rang noté sur la partie précédente
        lp_change = None
        if values[15]:
            prev = con.execute("""SELECT rank_div, rank_lp FROM games WHERE account_id = ? AND played_on <= ? AND rank_div IS NOT NULL
                                  ORDER BY played_on DESC, COALESCE(played_at, 0) DESC, id DESC LIMIT 1""", (acc["id"], values[1])).fetchone()
            if prev and values[16] is not None:
                lp_change = analysis.rank_value(values[15], values[16]) - analysis.rank_value(prev["rank_div"], prev["rank_lp"])
        con.execute("""INSERT INTO games (account_id, played_on, champ, enemy, result, kills, deaths, assists, deaths_pre15,
                       kp, cs_min, control_wards, obj_lost_free, focus, focus_ok, rank_div, rank_lp, lesson, lp_change)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", values + (lp_change,))
        if values[15]:
            con.execute("UPDATE accounts SET rank_div = ?, rank_lp = ? WHERE id = ?", (values[15], values[16], acc["id"]))
    flash(request, "Partie enregistrée.")
    return go("/games")


@app.post("/games/delete")
async def games_delete_many(request: Request):
    user = current_user(request)
    if not user:
        return go("/login")
    ids = [int(i) for i in (await request.form()).getlist("ids") if str(i).isdigit()]
    if ids:
        marks = ", ".join("?" * len(ids))
        mine = f"id IN ({marks}) AND account_id IN (SELECT id FROM accounts WHERE user_id = ?)"
        with db.connect() as con:
            # les parties importées supprimées ne reviennent pas à la synchronisation suivante
            con.execute(f"INSERT OR IGNORE INTO skipped (account_id, match_id) SELECT account_id, match_id FROM games WHERE match_id IS NOT NULL AND {mine}",
                        ids + [user["id"]])
            n = con.execute(f"DELETE FROM games WHERE {mine}", ids + [user["id"]]).rowcount
        flash(request, f"{n} partie{'s' if n > 1 else ''} supprimée{'s' if n > 1 else ''}.")
    return go("/games")


@app.post("/games/{game_id}/review")
def game_review(request: Request, game_id: int, focus: str = Form(""), focus_ok: str = Form(""), lesson: str = Form("")):
    user = current_user(request)
    if not user:
        return go("/login")
    with db.connect() as con:
        con.execute("""UPDATE games SET focus = ?, focus_ok = ?, lesson = ?, reviewed = 1
                       WHERE id = ? AND account_id IN (SELECT id FROM accounts WHERE user_id = ?)""",
                    (focus if focus in analysis.DRILL_INDEX else None, None if focus_ok == "" else int(focus_ok == "1"),
                     lesson.strip()[:500] or None, game_id, user["id"]))
    return go(f"/games#g{game_id}")


def delete_games(user, ids):
    with db.connect() as con:
        for game_id in ids:
            # une partie importée supprimée ne doit pas revenir à la synchronisation suivante
            con.execute("""INSERT OR IGNORE INTO skipped (account_id, match_id) SELECT account_id, match_id FROM games
                           WHERE id = ? AND match_id IS NOT NULL AND account_id IN (SELECT id FROM accounts WHERE user_id = ?)""",
                        (game_id, user["id"]))
            con.execute("DELETE FROM games WHERE id = ? AND account_id IN (SELECT id FROM accounts WHERE user_id = ?)", (game_id, user["id"]))


@app.post("/games/{game_id}/delete")
def game_delete(request: Request, game_id: int):
    user = current_user(request)
    if not user:
        return go("/login")
    delete_games(user, [game_id])
    flash(request, "Partie supprimée.")
    return go("/games")


# ---------- Counters ----------

@app.get("/counters")
def counters_page(request: Request, enemy: str = ""):
    user = current_user(request)
    if not user:
        return go("/login")
    acc, _ = active_account(request, user)
    if not acc:
        return go("/accounts")
    pool = get_pool(acc["id"])
    enemy = enemy if enemy in MU["champions"] else ""
    picks, best = analysis.counters(MU, pool, get_games(acc["id"]), enemy) if enemy else ([], [])
    champs = sorted(MU["champions"], key=lambda k: champ_name(k))
    return render(request, "counters.html", user, pool=pool, enemy=enemy, picks=picks, best=best, champs=champs,
                  early=analysis.EARLY, bans=analysis.suggested_bans(MU, pool) if pool else [])


# ---------- Administration ----------

@app.get("/admin")
def admin_page(request: Request):
    user = current_user(request)
    if not user or not user["is_admin"]:
        return go("/")
    with db.connect() as con:
        users = con.execute("""SELECT u.*, (SELECT COUNT(*) FROM accounts a WHERE a.user_id = u.id) AS n_accounts
                               FROM users u ORDER BY u.id""").fetchall()
    return render(request, "admin.html", user, users=users, signup=ALLOW_SIGNUP)


@app.post("/admin/matchups")
async def admin_matchups(request: Request, file: UploadFile = File(...)):
    global MU
    user = current_user(request)
    if not user or not user["is_admin"]:
        return go("/")
    try:
        raw = await file.read(5_000_001)
        assert len(raw) <= 5_000_000            # 5 Mo maximum
        data = json.loads(raw.decode("utf-8"))
        assert isinstance(data["champions"], dict) and data["ddragon"]
        sources = data["sources"] if "sources" in data else {"source": {"label": "source", "matchups": data["matchups"]}}
        assert sources
        for src in sources.values():
            assert src["label"]
            for opps in src["matchups"].values():
                for g, w in opps.values():
                    assert int(g) >= int(w) >= 0
    except Exception:
        flash(request, "Fichier refusé : ce n'est pas un jeu de matchups valide.", "err")
        return go("/admin")
    with open(analysis.OVERRIDE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    MU = analysis.load_matchups()
    flash(request, f"Matchups mis à jour : patch {data.get('patch', '?')}, {len(data['champions'])} champions, {len(sources)} source(s).")
    return go("/admin")


@app.post("/admin/users/{user_id}/delete")
def admin_user_delete(request: Request, user_id: int):
    user = current_user(request)
    if not user or not user["is_admin"] or user_id == user["id"]:
        return go("/admin")
    with db.connect() as con:
        con.execute("DELETE FROM users WHERE id = ?", (user_id,))
    flash(request, "Utilisateur supprimé.")
    return go("/admin")


@app.get("/healthz")
def healthz():
    return {"ok": True}
