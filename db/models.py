"""
WAR ROOM - Database Models v2
Simplified schema focused on Holdings and Transactions
"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    String, Text, Integer, DECIMAL, Date, 
    DateTime, Index, JSON, Float
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from db.database import Base


# ============================================================
# HOLDINGS - Current positions by broker
# ============================================================
class Holding(Base):
    """
    Represents a current position/holding in a broker.
    Each row = one asset in one broker.
    """
    __tablename__ = "holdings"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    # Core identification
    broker: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    isin: Mapped[Optional[str]] = mapped_column(String(12))  # Nullable for crypto
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Asset classification
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)  # STOCK, ETF, CRYPTO, COMMODITY, BOND
    
    # Position data
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(18, 8), nullable=False)
    purchase_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 8))  # Average cost basis
    purchase_date: Mapped[Optional[date]] = mapped_column(Date)  # First purchase date
    
    # Current valuation
    current_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 4))
    current_value: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)  # quantity * current_price (in EUR)
    native_current_value: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 2))  # Value in native currency
    exchange_rate_used: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 6))  # Rate used for conversion to EUR
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    
    # Tracking
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source_document: Mapped[Optional[str]] = mapped_column(String(255))  # File name
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Asset metadata (propagated from Transactions for valuation)
    share_class: Mapped[Optional[str]] = mapped_column(String(10))
    adr_ratio: Mapped[Optional[float]] = mapped_column(Float)
    nominal_value: Mapped[Optional[str]] = mapped_column(String(20))
    market: Mapped[Optional[str]] = mapped_column(String(10))
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_holdings_broker", "broker"),
        Index("idx_holdings_ticker", "ticker"),
        Index("idx_holdings_broker_ticker", "broker", "ticker"),
    )



# ============================================================
# TRANSACTIONS - Historical movements
# ============================================================
class Transaction(Base):
    """
    Represents a single transaction (buy, sell, dividend, etc).
    Historical record - never modified, only appended.
    """
    __tablename__ = "transactions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    # Core identification
    broker: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    isin: Mapped[Optional[str]] = mapped_column(String(12))  # Nullable for crypto
    
    # Transaction details
    operation: Mapped[str] = mapped_column(String(20), nullable=False)  # BUY, SELL, BALANCE, DIVIDEND, DEPOSIT, WITHDRAW, FEE, INTEREST
    status: Mapped[str] = mapped_column(String(20), default="COMPLETED") # COMPLETED, PENDING, CANCELLED
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(18, 8), nullable=False)
    price: Mapped[Decimal] = mapped_column(DECIMAL(18, 8), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    fees: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=Decimal("0"))
    
    # New fields for enhanced tracking
    realized_pnl: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 2))  # Realized P&L from this trade
    fx_cost: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 2))  # FX conversion cost

    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # Source tracking
    source_document: Mapped[Optional[str]] = mapped_column(String(255))  # File name
    source_page: Mapped[Optional[int]] = mapped_column(Integer)  # Page number in document
    
    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Asset metadata (primarily for stocks with complex structures)
    share_class: Mapped[Optional[str]] = mapped_column(String(10))  # "A", "B", "CL.B", etc.
    adr_ratio: Mapped[Optional[float]] = mapped_column(Float)  # 2.0 for ADR/2, 0.5 for 1/2
    nominal_value: Mapped[Optional[str]] = mapped_column(String(20))  # "0.001", "0.00", etc.
    market: Mapped[Optional[str]] = mapped_column(String(10))  # "DK", "US", "YC", etc.
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("idx_transactions_broker", "broker"),
        Index("idx_transactions_ticker", "ticker"),
        Index("idx_transactions_timestamp", "timestamp"),
    )


# ============================================================
# IMPORT LOG - Track imported documents
# ============================================================
class ImportLog(Base):
    """
    Tracks which documents have been imported.
    """
    __tablename__ = "import_log"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    broker: Mapped[str] = mapped_column(String(50), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(500))
    file_hash: Mapped[Optional[str]] = mapped_column(String(64))  # SHA256 to detect duplicates
    
    import_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    holdings_created: Mapped[int] = mapped_column(Integer, default=0)
    transactions_created: Mapped[int] = mapped_column(Integer, default=0)
    
    status: Mapped[str] = mapped_column(String(20), default="SUCCESS")  # SUCCESS, PARTIAL, FAILED
    errors: Mapped[Optional[dict]] = mapped_column(JSONB)
    

    __table_args__ = (
        Index("idx_import_log_broker", "broker"),
        Index("idx_import_log_filename", "filename"),
    )


# ============================================================
# COUNCIL SESSIONS - AI Strategic Consultations
# ============================================================
class CouncilSession(Base):
    """
    Stores historical sessions of The Council.
    Used for backtesting verdicts and auditing AI advice.
    """
    __tablename__ = "council_sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Input Data
    context_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False) # The "Dossier" (Portfolio Agg + Market Brief)
    
    # Output Data
    responses: Mapped[dict] = mapped_column(JSONB, nullable=False) # Raw JSON from 4 Advisors
    consensus: Mapped[Optional[str]] = mapped_column(Text) # Synthesized verdict (optional)
    consensus_model: Mapped[Optional[str]] = mapped_column(String(100)) # Ollama model used for consensus
    
    __table_args__ = (
        Index("idx_council_timestamp", "timestamp"),
    )


# ============================================================
# PRICE ALERTS - User-defined price notifications
# ============================================================
class PriceAlert(Base):
    """
    Stores price alerts set by users.
    When price crosses threshold, alert is triggered and notification sent.
    """
    __tablename__ = "price_alerts"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    # Target asset
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Alert configuration
    target_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 4), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # "above" or "below"
    
    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    triggered_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 4))
    
    # Notification settings
    notify_telegram: Mapped[bool] = mapped_column(default=True)
    notify_email: Mapped[bool] = mapped_column(default=False)
    
    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("idx_alerts_ticker", "ticker"),
        Index("idx_alerts_active", "is_active"),
    )


# ============================================================
# PORTFOLIO SNAPSHOTS - Daily portfolio value tracking
# ============================================================
class PortfolioSnapshot(Base):
    """
    Daily snapshot of portfolio value for historical tracking.
    Used for performance charts and analytics.
    """
    __tablename__ = "portfolio_snapshots"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    # Snapshot date (unique per day)
    snapshot_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    
    # Portfolio totals
    total_value: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=Decimal("0"))
    pnl_net: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=Decimal("0"))
    pnl_pct: Mapped[Decimal] = mapped_column(DECIMAL(10, 4), default=Decimal("0"))
    
    # Breakdown by broker (JSONB)
    # Format: {"IBKR": 15000.00, "BG SAXO": 8000.00, ...}
    broker_breakdown: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Breakdown by asset type (JSONB)
    # Format: {"STOCK": 12000.00, "ETF": 5000.00, "CRYPTO": 3000.00, ...}
    asset_breakdown: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Holdings count
    holdings_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("idx_snapshot_date", "snapshot_date"),
    )


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    broker: Mapped[str] = mapped_column(String(50))
    source_file: Mapped[str] = mapped_column(String(255))
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING, PROCESSED, APPLIED, ERROR
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Output from LLM
    validation_errors: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
