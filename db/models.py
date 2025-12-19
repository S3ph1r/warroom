"""
WAR ROOM - Database Models
All SQLAlchemy ORM models for the War Room system
"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    String, Text, Integer, Boolean, DECIMAL, Date, 
    DateTime, ForeignKey, CheckConstraint, Index, JSON
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from db.database import Base


# ============================================================
# TRANSACTIONS - Master ledger for all trades
# ============================================================
class Transaction(Base):
    __tablename__ = "transactions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ticker_symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    isin: Mapped[Optional[str]] = mapped_column(String(12))
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(18, 8), nullable=False)
    price_unit: Mapped[Decimal] = mapped_column(DECIMAL(18, 8), nullable=False)
    fiat_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    currency_original: Mapped[str] = mapped_column(String(3), default="EUR")
    currency_rate: Mapped[Decimal] = mapped_column(DECIMAL(10, 6), default=Decimal("1.0"))
    fees: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    csv_source: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    __table_args__ = (
        CheckConstraint(
            "operation_type IN ('BUY', 'SELL', 'DIVIDEND', 'DEPOSIT', 'WITHDRAW', 'FEE', 'INTEREST')",
            name="check_operation_type"
        ),
        CheckConstraint(
            "status IN ('PENDING', 'VERIFIED', 'ORPHAN', 'DELETED')",
            name="check_status"
        ),
        Index("idx_transactions_timestamp", "timestamp"),
    )


# ============================================================
# ASSETS REGISTRY - Master asset catalog
# ============================================================
class AssetRegistry(Base):
    __tablename__ = "assets_registry"
    
    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    isin: Mapped[Optional[str]] = mapped_column(String(12), unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(50), nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    exchange: Mapped[Optional[str]] = mapped_column(String(50))
    watch_level: Mapped[int] = mapped_column(Integer, default=1)
    risk_category: Mapped[Optional[str]] = mapped_column(String(20))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    __table_args__ = (
        CheckConstraint(
            "asset_class IN ('STOCK', 'ETF', 'CRYPTO', 'COMMODITY', 'BOND', 'CASH')",
            name="check_asset_class"
        ),
        CheckConstraint("watch_level BETWEEN 0 AND 3", name="check_watch_level"),
        CheckConstraint(
            "risk_category IN ('LOW', 'MEDIUM', 'HIGH', 'SPECULATIVE') OR risk_category IS NULL",
            name="check_risk_category"
        ),
    )


# ============================================================
# MARKET INTELLIGENCE - News and sentiment data
# ============================================================
class MarketIntelligence(Base):
    __tablename__ = "market_intelligence"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_level: Mapped[str] = mapped_column(String(10), nullable=False)
    trust_weight: Mapped[int] = mapped_column(Integer, nullable=False)
    related_tickers: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    title: Mapped[Optional[str]] = mapped_column(String(500))
    content_summary: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(Text)
    sentiment_score: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(3, 2))
    hype_volume: Mapped[Optional[int]] = mapped_column(Integer)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    __table_args__ = (
        CheckConstraint(
            "source_level IN ('ALPHA', 'BETA', 'GAMMA')",
            name="check_source_level"
        ),
        CheckConstraint("trust_weight BETWEEN 0 AND 100", name="check_trust_weight"),
        CheckConstraint(
            "sentiment_score BETWEEN -1 AND 1 OR sentiment_score IS NULL",
            name="check_sentiment_score"
        ),
    )


# ============================================================
# AI SCENARIOS - Generated market scenarios
# ============================================================
class AIScenario(Base):
    __tablename__ = "ai_scenarios"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    scenario_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    base_case: Mapped[Optional[str]] = mapped_column(Text)
    bull_case: Mapped[Optional[str]] = mapped_column(Text)
    bear_case: Mapped[Optional[str]] = mapped_column(Text)
    portfolio_impact: Mapped[Optional[dict]] = mapped_column(JSONB)
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(3, 2))
    sources_used: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    
    __table_args__ = (
        CheckConstraint(
            "scenario_type IN ('MACRO', 'SECTOR', 'TICKER', 'PORTFOLIO')",
            name="check_scenario_type"
        ),
    )


# ============================================================
# PORTFOLIO SNAPSHOTS - Daily portfolio state
# ============================================================
class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    total_value: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    total_invested: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    total_pnl: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    cash_balance: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    positions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    metrics: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ============================================================
# ALERTS - System notifications
# ============================================================
class Alert(Base):
    __tablename__ = "alerts"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    ticker_symbol: Mapped[Optional[str]] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    action_url: Mapped[Optional[str]] = mapped_column(Text)
    
    __table_args__ = (
        CheckConstraint(
            "severity IN ('INFO', 'WARNING', 'CRITICAL')",
            name="check_severity"
        ),
        CheckConstraint(
            "alert_type IN ('PRICE', 'NEWS', 'ORPHAN', 'SYSTEM', 'TAX', 'RISK')",
            name="check_alert_type"
        ),
    )


# ============================================================
# CSV IMPORT LOG - Track imported files
# ============================================================
class CSVImportLog(Base):
    __tablename__ = "csv_import_log"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    import_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    rows_processed: Mapped[int] = mapped_column(Integer, nullable=False)
    rows_inserted: Mapped[int] = mapped_column(Integer, nullable=False)
    rows_matched: Mapped[int] = mapped_column(Integer, nullable=False)
    errors: Mapped[Optional[dict]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="SUCCESS")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('SUCCESS', 'PARTIAL', 'FAILED')",
            name="check_import_status"
        ),
    )
