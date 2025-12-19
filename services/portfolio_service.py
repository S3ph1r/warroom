"""
WAR ROOM - Portfolio Query Service
Provides data access layer for dashboard
"""
import os
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, desc, and_, or_
from sqlalchemy.orm import Session
from db.database import SessionLocal, init_db
from db.models import Transaction, AssetRegistry, PortfolioSnapshot


def get_db_session() -> Session:
    """Get a database session"""
    return SessionLocal()


class PortfolioService:
    """Service for querying portfolio data"""
    
    def __init__(self):
        self.session = None
    
    def connect(self) -> bool:
        """Connect to database"""
        try:
            self.session = SessionLocal()
            return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False
    
    def close(self):
        """Close database session"""
        if self.session:
            self.session.close()
    
    def get_all_transactions(self, limit: int = 1000) -> List[Dict]:
        """Get all transactions from database"""
        transactions = self.session.query(Transaction).order_by(
            desc(Transaction.timestamp)
        ).limit(limit).all()
        
        return [{
            'id': str(tx.id),
            'timestamp': tx.timestamp,
            'ticker': tx.ticker_symbol,
            'isin': tx.isin,
            'operation_type': tx.operation_type,
            'quantity': float(tx.quantity) if tx.quantity else 0,
            'fiat_amount': float(tx.fiat_amount) if tx.fiat_amount else 0,
            'platform': tx.platform,
            'status': tx.status,
        } for tx in transactions]
    
    def get_transactions_by_platform(self) -> Dict[str, int]:
        """Get transaction count by platform"""
        results = self.session.query(
            Transaction.platform,
            func.count(Transaction.id)
        ).group_by(Transaction.platform).all()
        
        return {platform: count for platform, count in results}
    
    def get_transactions_by_type(self) -> Dict[str, int]:
        """Get transaction count by type"""
        results = self.session.query(
            Transaction.operation_type,
            func.count(Transaction.id)
        ).group_by(Transaction.operation_type).all()
        
        return {op_type: count for op_type, count in results}
    
    def get_holdings(self) -> List[Dict]:
        """
        Calculate current holdings based on transaction history.
        Groups transactions by ticker and sums quantities.
        """
        # Get all transactions grouped by ticker
        holdings = defaultdict(lambda: {
            'quantity': Decimal('0'),
            'total_invested': Decimal('0'),
            'earliest_date': None,
            'platforms': set(),
            'isin': None
        })
        
        transactions = self.session.query(Transaction).filter(
            Transaction.status == 'VERIFIED'
        ).all()
        
        for tx in transactions:
            ticker = tx.ticker_symbol
            if not ticker or ticker in ('UNKNOWN', '-', 'EUR', 'USD'):
                continue
            
            # Track ISIN
            if tx.isin:
                holdings[ticker]['isin'] = tx.isin
            
            # Track platforms
            if tx.platform:
                holdings[ticker]['platforms'].add(tx.platform)
            
            # Track earliest date
            if tx.timestamp:
                if not holdings[ticker]['earliest_date'] or tx.timestamp < holdings[ticker]['earliest_date']:
                    holdings[ticker]['earliest_date'] = tx.timestamp
            
            # Calculate quantity changes
            if tx.operation_type == 'BUY':
                if tx.quantity:
                    holdings[ticker]['quantity'] += tx.quantity
                if tx.fiat_amount:
                    holdings[ticker]['total_invested'] += abs(tx.fiat_amount)
            elif tx.operation_type == 'SELL':
                if tx.quantity:
                    holdings[ticker]['quantity'] -= abs(tx.quantity)
        
        # Convert to list and filter zero holdings
        result = []
        for ticker, data in holdings.items():
            qty = float(data['quantity'])
            if qty > 0.0001:  # Filter out dust
                result.append({
                    'ticker': ticker,
                    'isin': data['isin'],
                    'quantity': qty,
                    'total_invested': float(data['total_invested']),
                    'avg_price': float(data['total_invested'] / data['quantity']) if data['quantity'] > 0 else 0,
                    'platforms': list(data['platforms']),
                    'first_buy': data['earliest_date'],
                })
        
        return sorted(result, key=lambda x: x['total_invested'], reverse=True)
    
    def get_portfolio_summary(self) -> Dict:
        """Get overall portfolio summary"""
        # Total counts
        total_tx = self.session.query(func.count(Transaction.id)).scalar() or 0
        
        # Transaction totals by type
        by_type = self.get_transactions_by_type()
        by_platform = self.get_transactions_by_platform()
        
        # Date range
        first_tx = self.session.query(func.min(Transaction.timestamp)).scalar()
        last_tx = self.session.query(func.max(Transaction.timestamp)).scalar()
        
        # Total invested (sum of BUY transactions)
        total_invested = self.session.query(func.sum(Transaction.fiat_amount)).filter(
            Transaction.operation_type == 'BUY'
        ).scalar() or 0
        
        # Total sold (sum of SELL transactions)
        total_sold = self.session.query(func.sum(Transaction.fiat_amount)).filter(
            Transaction.operation_type == 'SELL'
        ).scalar() or 0
        
        # Dividends
        total_dividends = self.session.query(func.sum(Transaction.fiat_amount)).filter(
            Transaction.operation_type == 'DIVIDEND'
        ).scalar() or 0
        
        # Holdings
        holdings = self.get_holdings()
        
        return {
            'total_transactions': total_tx,
            'total_holdings': len(holdings),
            'transactions_by_type': by_type,
            'transactions_by_platform': by_platform,
            'first_transaction': first_tx,
            'last_transaction': last_tx,
            'total_invested': abs(float(total_invested)) if total_invested else 0,
            'total_sold': float(total_sold) if total_sold else 0,
            'total_dividends': float(total_dividends) if total_dividends else 0,
            'holdings': holdings,
        }
    
    def get_monthly_activity(self, months: int = 12) -> List[Dict]:
        """Get monthly transaction activity"""
        cutoff = datetime.now() - timedelta(days=months * 30)
        
        transactions = self.session.query(Transaction).filter(
            Transaction.timestamp >= cutoff
        ).all()
        
        # Group by month
        monthly = defaultdict(lambda: {'buys': 0, 'sells': 0, 'dividends': 0, 'amount': Decimal('0')})
        
        for tx in transactions:
            if tx.timestamp:
                month_key = tx.timestamp.strftime('%Y-%m')
                if tx.operation_type == 'BUY':
                    monthly[month_key]['buys'] += 1
                elif tx.operation_type == 'SELL':
                    monthly[month_key]['sells'] += 1
                elif tx.operation_type == 'DIVIDEND':
                    monthly[month_key]['dividends'] += 1
                if tx.fiat_amount:
                    monthly[month_key]['amount'] += tx.fiat_amount
        
        return [
            {'month': k, **{key: float(v) if isinstance(v, Decimal) else v for key, v in data.items()}}
            for k, data in sorted(monthly.items())
        ]


def get_portfolio_data() -> Dict:
    """
    Get portfolio data for dashboard.
    Returns dict with holdings and metrics.
    """
    service = PortfolioService()
    
    if not service.connect():
        return {'error': 'Database connection failed'}
    
    try:
        summary = service.get_portfolio_summary()
        return summary
    finally:
        service.close()


if __name__ == "__main__":
    print("\n🎯 WAR ROOM Portfolio Query Service")
    print("=" * 50)
    
    service = PortfolioService()
    
    if not service.connect():
        print("❌ Cannot connect to database")
        sys.exit(1)
    
    try:
        summary = service.get_portfolio_summary()
        
        print(f"\n📊 Portfolio Summary")
        print(f"   Total Transactions: {summary['total_transactions']}")
        print(f"   Total Holdings: {summary['total_holdings']}")
        print(f"   First Transaction: {summary['first_transaction']}")
        print(f"   Last Transaction: {summary['last_transaction']}")
        
        print(f"\n💰 Financials")
        print(f"   Total Invested: €{summary['total_invested']:,.2f}")
        print(f"   Total Sold: €{summary['total_sold']:,.2f}")
        print(f"   Total Dividends: €{summary['total_dividends']:,.2f}")
        
        print(f"\n📈 By Platform:")
        for platform, count in summary['transactions_by_platform'].items():
            print(f"   {platform}: {count}")
        
        print(f"\n📋 Top 10 Holdings:")
        for i, h in enumerate(summary['holdings'][:10]):
            print(f"   {i+1}. {h['ticker']:12} | Qty: {h['quantity']:.4f} | Invested: €{h['total_invested']:,.2f}")
        
    finally:
        service.close()
