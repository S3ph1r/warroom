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
    DateTime, Index, JSON
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
    current_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 8))
    current_value: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)  # quantity * current_price
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    
    # Tracking
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source_document: Mapped[Optional[str]] = mapped_column(String(255))  # File name
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_holdings_broker", "broker"),
        Index("idx_holdings_ticker", "ticker"),
        Index("idx_holdings_broker_ticker", "broker", "ticker", unique=True),
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
    operation: Mapped[str] = mapped_column(String(20), nullable=False)  # BUY, SELL, DIVIDEND, DEPOSIT, WITHDRAW, FEE, INTEREST
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(18, 8), nullable=False)
    price: Mapped[Decimal] = mapped_column(DECIMAL(18, 8), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    fees: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=Decimal("0"))
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # Source tracking
    source_document: Mapped[Optional[str]] = mapped_column(String(255))  # File name
    source_page: Mapped[Optional[int]] = mapped_column(Integer)  # Page number in document
    
    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text)
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
