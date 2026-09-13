from __future__ import annotations
import json
from datetime import datetime
from typing import Optional

import psycopg
from psycopg.rows import dict_row

from .ingestion_models import AuctionCandidate, AuctionSource
from .time_utils import utcnow_naive


class PostgresAuctionRepository:
    """PostgreSQL repository used in production when DATABASE_URL is available."""

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._init()

    def _connect(self):
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def _init(self):
        with self._connect() as con, con.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS auctions (
                    fingerprint TEXT PRIMARY KEY,
                    canonical_id TEXT,
                    source_id TEXT,
                    court TEXT,
                    procedure_number TEXT,
                    lot_number TEXT,
                    city TEXT,
                    province TEXT,
                    property_type TEXT,
                    minimum_bid DOUBLE PRECISION,
                    base_price DOUBLE PRECISION,
                    auction_date TIMESTAMP,
                    asta_score INTEGER,
                    confidence_score INTEGER,
                    profile TEXT,
                    updated_at TIMESTAMP NOT NULL,
                    payload JSONB NOT NULL
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS ix_auctions_city ON auctions(city)")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_auctions_province ON auctions(province)")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_auctions_auction_date ON auctions(auction_date)")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_auctions_minimum_bid ON auctions(minimum_bid)")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_auctions_score ON auctions(asta_score)")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_auctions_canonical ON auctions(canonical_id)")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    fingerprint TEXT PRIMARY KEY,
                    asta_score INTEGER,
                    confidence_score INTEGER,
                    profile TEXT,
                    updated_at TIMESTAMP NOT NULL,
                    payload JSONB NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sources (
                    source_id TEXT PRIMARY KEY,
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """)

    def save_source(self, source: AuctionSource):
        payload = source.model_dump(mode="json")
        with self._connect() as con, con.cursor() as cur:
            cur.execute(
                """INSERT INTO sources(source_id,payload,updated_at) VALUES(%s,%s::jsonb,%s)
                ON CONFLICT(source_id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at""",
                (source.id, json.dumps(payload), utcnow_naive()),
            )

    def load_sources(self) -> list[AuctionSource]:
        with self._connect() as con, con.cursor() as cur:
            cur.execute("SELECT payload FROM sources")
            rows = cur.fetchall()
        out = []
        for row in rows:
            try:
                out.append(AuctionSource.model_validate(row["payload"]))
            except Exception:
                continue
        return out

    def save_auction(self, auction: AuctionCandidate, analysis=None):
        if not auction.fingerprint:
            return
        asta_score = getattr(analysis, "asta_score", None) if analysis is not None else None
        confidence = getattr(analysis, "confidence_score", None) if analysis is not None else None
        profile = getattr(analysis, "profile", None) if analysis is not None else None
        payload = auction.model_dump(mode="json")
        with self._connect() as con, con.cursor() as cur:
            cur.execute(
                """
                INSERT INTO auctions(
                    fingerprint,canonical_id,source_id,court,procedure_number,lot_number,
                    city,province,property_type,minimum_bid,base_price,auction_date,
                    asta_score,confidence_score,profile,updated_at,payload
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    canonical_id=excluded.canonical_id, source_id=excluded.source_id,
                    court=excluded.court, procedure_number=excluded.procedure_number,
                    lot_number=excluded.lot_number, city=excluded.city, province=excluded.province,
                    property_type=excluded.property_type, minimum_bid=excluded.minimum_bid,
                    base_price=excluded.base_price, auction_date=excluded.auction_date,
                    asta_score=COALESCE(excluded.asta_score,auctions.asta_score),
                    confidence_score=COALESCE(excluded.confidence_score,auctions.confidence_score),
                    profile=COALESCE(excluded.profile,auctions.profile),
                    updated_at=excluded.updated_at, payload=excluded.payload
                """,
                (
                    auction.fingerprint, auction.canonical_id, auction.source_id, auction.court,
                    auction.procedure_number, auction.lot_number, auction.city, auction.province,
                    auction.property_type, auction.minimum_bid, auction.base_price, auction.auction_date,
                    asta_score, confidence, profile, utcnow_naive(), json.dumps(payload),
                ),
            )

    def save_analysis(self, fingerprint: str, result):
        payload = result.model_dump(mode="json")
        with self._connect() as con, con.cursor() as cur:
            cur.execute(
                """INSERT INTO analyses(fingerprint,asta_score,confidence_score,profile,updated_at,payload)
                VALUES(%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    asta_score=excluded.asta_score, confidence_score=excluded.confidence_score,
                    profile=excluded.profile, updated_at=excluded.updated_at, payload=excluded.payload""",
                (fingerprint, result.asta_score, result.confidence_score, result.profile, utcnow_naive(), json.dumps(payload)),
            )
            cur.execute(
                "UPDATE auctions SET asta_score=%s, confidence_score=%s, profile=%s, updated_at=%s WHERE fingerprint=%s",
                (result.asta_score, result.confidence_score, result.profile, utcnow_naive(), fingerprint),
            )

    def get_auction(self, fingerprint: str) -> Optional[dict]:
        with self._connect() as con, con.cursor() as cur:
            cur.execute("SELECT payload FROM auctions WHERE fingerprint=%s", (fingerprint,))
            row = cur.fetchone()
        return row["payload"] if row else None

    def load_auction_models(self) -> list[AuctionCandidate]:
        with self._connect() as con, con.cursor() as cur:
            cur.execute("SELECT payload FROM auctions")
            rows = cur.fetchall()
        out = []
        for row in rows:
            try:
                out.append(AuctionCandidate.model_validate(row["payload"]))
            except Exception:
                continue
        return out

    def search_auctions(self, *, limit=50, offset=0, city=None, province=None, property_type=None,
                        min_bid=None, max_bid=None, score_min=None, profiles=None, active_after: datetime | None=None) -> dict:
        clauses = ["1=1"]
        params = []
        if city:
            clauses.append("LOWER(city)=LOWER(%s)"); params.append(city)
        if province:
            clauses.append("LOWER(province)=LOWER(%s)"); params.append(province)
        if property_type:
            clauses.append("LOWER(property_type) LIKE LOWER(%s)"); params.append(f"%{property_type}%")
        if min_bid is not None:
            clauses.append("minimum_bid>=%s"); params.append(min_bid)
        if max_bid is not None:
            clauses.append("minimum_bid<=%s"); params.append(max_bid)
        if score_min is not None:
            clauses.append("asta_score>=%s"); params.append(score_min)
        if profiles:
            clauses.append("profile = ANY(%s)"); params.append(profiles)
        if active_after:
            clauses.append("auction_date>=%s"); params.append(active_after)
        where = " AND ".join(clauses)
        with self._connect() as con, con.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS n FROM auctions WHERE {where}", params)
            total = cur.fetchone()["n"]
            cur.execute(
                f"SELECT payload,asta_score,confidence_score,profile FROM auctions WHERE {where} "
                "ORDER BY auction_date NULLS LAST, asta_score DESC NULLS LAST LIMIT %s OFFSET %s",
                [*params, limit, offset],
            )
            rows = cur.fetchall()
        items = []
        for row in rows:
            payload = dict(row["payload"])
            payload["asta_score"] = row["asta_score"]
            payload["confidence_score"] = row["confidence_score"]
            payload["profile"] = row["profile"]
            items.append(payload)
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def list_auctions(self, limit: int = 100):
        return self.search_auctions(limit=limit)["items"]

    def get_analysis(self, fingerprint: str):
        with self._connect() as con, con.cursor() as cur:
            cur.execute("SELECT payload FROM analyses WHERE fingerprint=%s", (fingerprint,))
            row = cur.fetchone()
        return row["payload"] if row else None
