from __future__ import annotations
import hashlib, hmac, os, secrets, sqlite3, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import HTTPException, Header
from pydantic import BaseModel, Field

DB_PATH = Path(os.getenv('ASTAPILOT_DB', '/mnt/data/astapilot_data.sqlite3'))
SESSION_DAYS = int(os.getenv('ASTAPILOT_SESSION_DAYS', '30'))

PLANS = {
    'FREE': {'name':'Free','price_monthly':0,'entitlements':['BASIC_SCORE','FAVORITES']},
    'PLUS': {'name':'Plus','price_monthly':24.90,'entitlements':['BASIC_SCORE','FAVORITES','FULL_ANALYSIS','FULL_RISK_DETAILS','DOCUMENT_PROVENANCE','SIMULATOR','PERSONAL_BID_LIMIT','COPILOT','SAVED_SEARCHES','ALERTS']},
    'INVESTOR': {'name':'Investor','price_monthly':79.90,'entitlements':['BASIC_SCORE','FAVORITES','FULL_ANALYSIS','FULL_RISK_DETAILS','DOCUMENT_PROVENANCE','SIMULATOR','PERSONAL_BID_LIMIT','COPILOT','SAVED_SEARCHES','ALERTS','COMPARISON','DEAL_RADAR','PORTFOLIO','ROI_TOOLS','EXPORT']},
    'PRO': {'name':'Pro','price_monthly':199.0,'entitlements':['*']},
}

class RegisterIn(BaseModel):
    name: str = Field(min_length=2,max_length=80)
    email: str
    password: str = Field(min_length=8,max_length=128)

class LoginIn(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: str
    name: str
    email: str
    plan: str
    entitlements: list[str]


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con=sqlite3.connect(DB_PATH)
    con.row_factory=sqlite3.Row
    return con

def init_auth():
    with _connect() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS users(
            id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, plan TEXT NOT NULL DEFAULT 'FREE', created_at TEXT NOT NULL)''')
        con.execute('''CREATE TABLE IF NOT EXISTS sessions(
            token TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id))''')
        con.execute('''CREATE TABLE IF NOT EXISTS favorites(
            user_id TEXT NOT NULL, fingerprint TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(user_id,fingerprint))''')
        con.execute('''CREATE TABLE IF NOT EXISTS purchases(
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, product_code TEXT NOT NULL,
            auction_fingerprint TEXT, amount REAL, currency TEXT DEFAULT 'EUR', status TEXT NOT NULL,
            external_id TEXT, created_at TEXT NOT NULL)''')
        con.execute('''CREATE TABLE IF NOT EXISTS billing_subscriptions(
            external_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, plan TEXT NOT NULL,
            status TEXT NOT NULL, updated_at TEXT NOT NULL)''')
        con.execute('''CREATE TABLE IF NOT EXISTS payment_events(
            event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, received_at TEXT NOT NULL)''')

def _hash_password(password:str)->str:
    salt=secrets.token_bytes(16)
    dk=hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 210000)
    return f'pbkdf2_sha256$210000${salt.hex()}${dk.hex()}'

def _verify(password:str, stored:str)->bool:
    try:
        algo, rounds, salt_hex, digest_hex=stored.split('$')
        calc=hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(calc.hex(), digest_hex)
    except Exception:
        return False

def _make_session(user_id:str)->str:
    token=secrets.token_urlsafe(40)
    exp=datetime.now(timezone.utc)+timedelta(days=SESSION_DAYS)
    with _connect() as con:
        con.execute('INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)',(token,user_id,exp.isoformat()))
    return token

def _to_user(row)->UserOut:
    plan=row['plan'] if row['plan'] in PLANS else 'FREE'
    return UserOut(id=row['id'],name=row['name'],email=row['email'],plan=plan,entitlements=PLANS[plan]['entitlements'])

def register(data:RegisterIn):
    init_auth(); uid=str(uuid.uuid4()); now=datetime.now(timezone.utc).isoformat()
    try:
        with _connect() as con:
            con.execute('INSERT INTO users(id,name,email,password_hash,created_at) VALUES(?,?,?,?,?)',(uid,data.name.strip(),data.email.lower(),_hash_password(data.password),now))
    except sqlite3.IntegrityError:
        raise HTTPException(409,'Email già registrata')
    return {'token':_make_session(uid),'user':get_user(uid)}

def login(data:LoginIn):
    init_auth()
    with _connect() as con:
        row=con.execute('SELECT * FROM users WHERE email=?',(data.email.lower(),)).fetchone()
    if not row or not _verify(data.password,row['password_hash']):
        raise HTTPException(401,'Credenziali non valide')
    return {'token':_make_session(row['id']),'user':_to_user(row)}

def get_user(user_id:str)->UserOut:
    with _connect() as con:
        row=con.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone()
    if not row: raise HTTPException(404,'Utente non trovato')
    return _to_user(row)

def require_user(authorization: str | None = Header(default=None)) -> UserOut:
    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(401,'Autenticazione richiesta')
    token=authorization.split(' ',1)[1]
    with _connect() as con:
        row=con.execute('''SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
                           WHERE s.token=? AND s.expires_at>?''',(token,datetime.now(timezone.utc).isoformat())).fetchone()
    if not row: raise HTTPException(401,'Sessione non valida o scaduta')
    return _to_user(row)

def logout(authorization: str | None):
    if authorization and authorization.lower().startswith('bearer '):
        token=authorization.split(' ',1)[1]
        with _connect() as con: con.execute('DELETE FROM sessions WHERE token=?',(token,))

def list_favorites(user_id:str)->list[str]:
    with _connect() as con:
        rows=con.execute('SELECT fingerprint FROM favorites WHERE user_id=? ORDER BY created_at DESC',(user_id,)).fetchall()
    return [r['fingerprint'] for r in rows]

def set_favorite(user_id:str,fingerprint:str, enabled:bool):
    with _connect() as con:
        if enabled:
            con.execute('INSERT OR IGNORE INTO favorites(user_id,fingerprint,created_at) VALUES(?,?,?)',(user_id,fingerprint,datetime.now(timezone.utc).isoformat()))
        else:
            con.execute('DELETE FROM favorites WHERE user_id=? AND fingerprint=?',(user_id,fingerprint))

def set_plan(user_id:str,plan:str):
    if plan not in PLANS: raise HTTPException(400,'Piano non valido')
    with _connect() as con: con.execute('UPDATE users SET plan=? WHERE id=?',(plan,user_id))
