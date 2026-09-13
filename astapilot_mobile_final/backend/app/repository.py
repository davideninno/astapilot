from __future__ import annotations
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .ingestion_models import AuctionCandidate, AuctionSource
from .time_utils import utcnow_naive

DB_PATH = Path(os.getenv("ASTAPILOT_DB", "/mnt/data/astapilot_data.sqlite3"))


class AuctionRepository:
    """SQLite repository for local/dev use; production can switch to PostgreSQL."""
    def __init__(self, path: Path = DB_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def _init(self):
        with self._connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS auctions (
                fingerprint TEXT PRIMARY KEY, canonical_id TEXT, source_id TEXT, court TEXT,
                procedure_number TEXT, lot_number TEXT, city TEXT, province TEXT, property_type TEXT,
                minimum_bid REAL, base_price REAL, auction_date TEXT, asta_score INTEGER,
                confidence_score INTEGER, profile TEXT, updated_at TEXT NOT NULL, payload TEXT NOT NULL)""")
            existing = {row[1] for row in con.execute("PRAGMA table_info(auctions)").fetchall()}
            for name, ddl in {"canonical_id":"TEXT","source_id":"TEXT","court":"TEXT","procedure_number":"TEXT","lot_number":"TEXT","city":"TEXT","province":"TEXT","property_type":"TEXT","minimum_bid":"REAL","base_price":"REAL","auction_date":"TEXT","asta_score":"INTEGER","confidence_score":"INTEGER","profile":"TEXT","updated_at":"TEXT"}.items():
                if name not in existing: con.execute(f"ALTER TABLE auctions ADD COLUMN {name} {ddl}")
            con.execute("UPDATE auctions SET updated_at=COALESCE(updated_at, ?)", (utcnow_naive().isoformat(),))
            for name, col in [("city","city"),("province","province"),("auction_date","auction_date"),("minimum_bid","minimum_bid"),("score","asta_score"),("canonical","canonical_id")]:
                con.execute(f"CREATE INDEX IF NOT EXISTS ix_auctions_{name} ON auctions({col})")
            con.execute("""CREATE TABLE IF NOT EXISTS analyses (
                fingerprint TEXT PRIMARY KEY, asta_score INTEGER, confidence_score INTEGER,
                profile TEXT, updated_at TEXT NOT NULL, payload TEXT NOT NULL)""")
            con.execute("""CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL)""")

    def save_source(self, source: AuctionSource):
        with self._connect() as con:
            con.execute("INSERT INTO sources(source_id,payload,updated_at) VALUES(?,?,?) ON CONFLICT(source_id) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at", (source.id,source.model_dump_json(),utcnow_naive().isoformat()))

    def load_sources(self):
        with self._connect() as con: rows=con.execute("SELECT payload FROM sources").fetchall()
        out=[]
        for row in rows:
            try: out.append(AuctionSource.model_validate_json(row["payload"]))
            except Exception: continue
        return out

    def save_auction(self, auction: AuctionCandidate, analysis=None):
        if not auction.fingerprint: return
        score=getattr(analysis,"asta_score",None) if analysis is not None else None
        confidence=getattr(analysis,"confidence_score",None) if analysis is not None else None
        profile=getattr(analysis,"profile",None) if analysis is not None else None
        with self._connect() as con:
            con.execute("""INSERT INTO auctions(fingerprint,canonical_id,source_id,court,procedure_number,lot_number,city,province,property_type,minimum_bid,base_price,auction_date,asta_score,confidence_score,profile,updated_at,payload)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(fingerprint) DO UPDATE SET canonical_id=excluded.canonical_id,source_id=excluded.source_id,court=excluded.court,procedure_number=excluded.procedure_number,lot_number=excluded.lot_number,city=excluded.city,province=excluded.province,property_type=excluded.property_type,minimum_bid=excluded.minimum_bid,base_price=excluded.base_price,auction_date=excluded.auction_date,asta_score=COALESCE(excluded.asta_score,auctions.asta_score),confidence_score=COALESCE(excluded.confidence_score,auctions.confidence_score),profile=COALESCE(excluded.profile,auctions.profile),updated_at=excluded.updated_at,payload=excluded.payload""",
            (auction.fingerprint,auction.canonical_id,auction.source_id,auction.court,auction.procedure_number,auction.lot_number,auction.city,auction.province,auction.property_type,auction.minimum_bid,auction.base_price,auction.auction_date.isoformat() if auction.auction_date else None,score,confidence,profile,utcnow_naive().isoformat(),auction.model_dump_json()))

    def save_analysis(self,fingerprint,result):
        with self._connect() as con:
            con.execute("INSERT INTO analyses(fingerprint,asta_score,confidence_score,profile,updated_at,payload) VALUES(?,?,?,?,?,?) ON CONFLICT(fingerprint) DO UPDATE SET asta_score=excluded.asta_score,confidence_score=excluded.confidence_score,profile=excluded.profile,updated_at=excluded.updated_at,payload=excluded.payload",(fingerprint,result.asta_score,result.confidence_score,result.profile,utcnow_naive().isoformat(),result.model_dump_json()))
            con.execute("UPDATE auctions SET asta_score=?,confidence_score=?,profile=?,updated_at=? WHERE fingerprint=?",(result.asta_score,result.confidence_score,result.profile,utcnow_naive().isoformat(),fingerprint))

    def get_auction(self,fingerprint):
        with self._connect() as con: row=con.execute("SELECT payload FROM auctions WHERE fingerprint=?",(fingerprint,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def load_auction_models(self):
        with self._connect() as con: rows=con.execute("SELECT payload FROM auctions").fetchall()
        out=[]
        for row in rows:
            try: out.append(AuctionCandidate.model_validate_json(row["payload"]))
            except Exception: continue
        return out

    def search_auctions(self,*,limit=50,offset=0,city=None,province=None,property_type=None,min_bid=None,max_bid=None,score_min=None,profiles=None,active_after:datetime|None=None):
        clauses=["1=1"]; params=[]
        if city: clauses.append("LOWER(city)=LOWER(?)"); params.append(city)
        if province: clauses.append("LOWER(province)=LOWER(?)"); params.append(province)
        if property_type: clauses.append("LOWER(property_type) LIKE LOWER(?)"); params.append(f"%{property_type}%")
        if min_bid is not None: clauses.append("minimum_bid>=?"); params.append(min_bid)
        if max_bid is not None: clauses.append("minimum_bid<=?"); params.append(max_bid)
        if score_min is not None: clauses.append("asta_score>=?"); params.append(score_min)
        if profiles:
            marks=",".join("?" for _ in profiles); clauses.append(f"profile IN ({marks})"); params.extend(profiles)
        if active_after: clauses.append("auction_date>=?"); params.append(active_after.isoformat())
        where=" AND ".join(clauses)
        with self._connect() as con:
            total=con.execute(f"SELECT COUNT(*) AS n FROM auctions WHERE {where}",params).fetchone()["n"]
            rows=con.execute(f"SELECT payload,asta_score,confidence_score,profile FROM auctions WHERE {where} ORDER BY CASE WHEN auction_date IS NULL THEN 1 ELSE 0 END,auction_date ASC,asta_score DESC LIMIT ? OFFSET ?",[*params,limit,offset]).fetchall()
        items=[]
        for row in rows:
            payload=json.loads(row["payload"]); payload["asta_score"]=row["asta_score"]; payload["confidence_score"]=row["confidence_score"]; payload["profile"]=row["profile"]; items.append(payload)
        return {"items":items,"total":total,"limit":limit,"offset":offset}

    def list_auctions(self,limit=100): return self.search_auctions(limit=limit)["items"]
    def get_analysis(self,fingerprint):
        with self._connect() as con: row=con.execute("SELECT payload FROM analyses WHERE fingerprint=?",(fingerprint,)).fetchone()
        return json.loads(row["payload"]) if row else None


def _build_repository():
    dsn=os.getenv("DATABASE_URL","").strip()
    if dsn.startswith(("postgres://","postgresql://")):
        from .postgres_repository import PostgresAuctionRepository
        return PostgresAuctionRepository(dsn)
    return AuctionRepository()


repository=_build_repository()
