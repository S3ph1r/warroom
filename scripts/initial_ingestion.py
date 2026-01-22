"""
Master Initial Ingestion Script
================================
Runs all broker parsers in sequence with:
- Dynamic file discovery for each broker
- Stop on error with checkpoint saving
- Resume from last checkpoint capability
- Final reconciliation report
"""
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction


# Checkpoint file path
CHECKPOINT_FILE = Path(__file__).parent / '.ingestion_checkpoint.json'


# Broker folder paths
BROKER_FOLDERS = {
    'BG_SAXO': Path(r'D:\Download\BGSAXO'),
    'TRADE_REPUBLIC': Path(r'D:\Download\Trade Repubblic'),
    'IBKR': Path(r'D:\Download\IBKR'),
    'SCALABLE': Path(r'D:\Download\SCALABLE CAPITAL'),
    'REVOLUT': Path(r'D:\Download\Revolut'),
    'BINANCE': Path(r'D:\Download\Binance'),
}


# Ingestion steps in order
INGESTION_STEPS = [
    {'id': 1, 'name': 'clear_database', 'description': 'Clear all existing data'},
    {'id': 2, 'name': 'bgsaxo_holdings', 'description': 'BG Saxo Holdings', 'script': 'parse_bgsaxo_holdings.py'},
    {'id': 3, 'name': 'bgsaxo_transactions', 'description': 'BG Saxo Transactions', 'script': 'parse_bgsaxo_transactions.py'},
    {'id': 4, 'name': 'trade_republic', 'description': 'Trade Republic', 'script': 'parse_trade_republic.py'},
    {'id': 5, 'name': 'ibkr', 'description': 'IBKR', 'script': 'parse_ibkr.py'},
    {'id': 6, 'name': 'scalable_holdings', 'description': 'Scalable Holdings', 'script': 'parse_scalable.py'},
    {'id': 7, 'name': 'scalable_transactions', 'description': 'Scalable Transactions', 'script': 'parse_scalable_transactions.py'},
    {'id': 8, 'name': 'revolut_stocks', 'description': 'Revolut Stocks', 'script': 'parse_revolut_stocks.py'},
    {'id': 9, 'name': 'revolut_crypto_holdings', 'description': 'Revolut Crypto Holdings', 'script': 'parse_revolut_crypto.py'},
    {'id': 10, 'name': 'revolut_crypto_transactions', 'description': 'Revolut Crypto Transactions', 'script': 'parse_revolut_crypto_transactions.py'},
    {'id': 11, 'name': 'revolut_commodities', 'description': 'Revolut Commodities (Gold/Silver)', 'script': 'parse_revolut_commodities.py'},
    {'id': 12, 'name': 'binance', 'description': 'Binance', 'script': 'parse_binance.py'},
    {'id': 13, 'name': 'reconciliation', 'description': 'Generate Reconciliation Report'},
]


def load_checkpoint() -> dict:
    """Load checkpoint from file."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return {'last_completed_step': 0, 'started_at': None}


def save_checkpoint(step_id: int):
    """Save checkpoint to file."""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({
            'last_completed_step': step_id,
            'saved_at': datetime.now().isoformat()
        }, f)


def clear_checkpoint():
    """Clear checkpoint file."""
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()


def clear_database():
    """Clear all holdings and transactions from database."""
    session = SessionLocal()
    
    try:
        holdings_count = session.query(Holding).delete()
        transactions_count = session.query(Transaction).delete()
        session.commit()
        print(f"  ✅ Cleared {holdings_count} holdings, {transactions_count} transactions")
        return True
    except Exception as e:
        session.rollback()
        print(f"  ❌ Error clearing database: {e}")
        return False
    finally:
        session.close()


def run_parser_script(script_name: str) -> bool:
    """Run a parser script and return success status."""
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        print(f"  [ERROR] Script not found: {script_path}")
        return False
    
    try:
        # Get Python executable from virtual environment
        venv_python = Path(__file__).parent.parent / 'venv' / 'Scripts' / 'python.exe'
        if not venv_python.exists():
            venv_python = 'python'
        
        # Set UTF-8 encoding for subprocess
        import os
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run(
            [str(venv_python), str(script_path)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
            env=env,
            encoding='utf-8',
            errors='replace'
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        
        if result.returncode != 0:
            print(f"  [ERROR] Script failed with exit code {result.returncode}")
            if result.stderr:
                print(f"  Error: {result.stderr[:500]}")
            return False
        
        return True
        
    except Exception as e:
        print(f"  [ERROR] Error running script: {e}")
        return False


def generate_reconciliation_report():
    """Generate reconciliation report comparing holdings vs transactions."""
    print("\n" + "=" * 70)
    print("📊 RECONCILIATION REPORT")
    print("=" * 70)
    
    session = SessionLocal()
    
    # Get all holdings
    holdings = session.query(Holding).all()
    
    # Get all transactions
    transactions = session.query(Transaction).all()
    
    # Summary by broker
    print("\n📋 HOLDINGS BY BROKER")
    print("-" * 50)
    
    broker_holdings = {}
    total_holdings_value = Decimal('0')
    
    for h in holdings:
        if h.broker not in broker_holdings:
            broker_holdings[h.broker] = {'count': 0, 'value': Decimal('0'), 'cash': Decimal('0')}
        broker_holdings[h.broker]['count'] += 1
        broker_holdings[h.broker]['value'] += h.current_value or Decimal('0')
        if h.asset_type == 'CASH':
            broker_holdings[h.broker]['cash'] += h.quantity or Decimal('0')
        total_holdings_value += h.current_value or Decimal('0')
    
    for broker, data in sorted(broker_holdings.items()):
        print(f"  {broker:<20} | {data['count']:>3} holdings | €{data['value']:>12,.2f} | Cash: €{data['cash']:>10,.2f}")
    
    print(f"\n  {'TOTAL':<20} | {len(holdings):>3} holdings | €{total_holdings_value:>12,.2f}")
    
    # Transactions summary
    print("\n📋 TRANSACTIONS BY BROKER")
    print("-" * 50)
    
    broker_transactions = {}
    for t in transactions:
        if t.broker not in broker_transactions:
            broker_transactions[t.broker] = {'count': 0, 'buys': 0, 'sells': 0, 'other': 0}
        broker_transactions[t.broker]['count'] += 1
        if t.operation == 'BUY':
            broker_transactions[t.broker]['buys'] += 1
        elif t.operation == 'SELL':
            broker_transactions[t.broker]['sells'] += 1
        else:
            broker_transactions[t.broker]['other'] += 1
    
    for broker, data in sorted(broker_transactions.items()):
        print(f"  {broker:<20} | {data['count']:>5} TX | Buys: {data['buys']:>4} | Sells: {data['sells']:>4} | Other: {data['other']:>4}")
    
    print(f"\n  {'TOTAL':<20} | {len(transactions):>5} TX")
    
    # Reconciliation: compare holdings vs calculated from transactions
    print("\n📋 HOLDINGS vs TRANSACTIONS RECONCILIATION")
    print("-" * 50)
    print("  (Comparing actual holdings with net positions from buy/sell history)")
    
    # Calculate net positions from transactions
    tx_positions = {}
    for t in transactions:
        key = (t.broker, t.ticker)
        if key not in tx_positions:
            tx_positions[key] = Decimal('0')
        
        if t.operation == 'BUY':
            tx_positions[key] += t.quantity or Decimal('0')
        elif t.operation == 'SELL':
            tx_positions[key] -= t.quantity or Decimal('0')
    
    # Compare with actual holdings
    discrepancies = []
    for h in holdings:
        if h.asset_type == 'CASH':
            continue
        
        key = (h.broker, h.ticker)
        tx_qty = tx_positions.get(key, Decimal('0'))
        actual_qty = h.quantity or Decimal('0')
        
        diff = actual_qty - tx_qty
        if abs(diff) > Decimal('0.01'):  # Threshold for reporting
            discrepancies.append({
                'broker': h.broker,
                'ticker': h.ticker,
                'actual': actual_qty,
                'calculated': tx_qty,
                'difference': diff
            })
    
    if discrepancies:
        print("\n  ⚠️  Discrepancies found (transaction history may be incomplete):")
        for d in discrepancies[:20]:  # Limit to 20
            print(f"    {d['broker']:<15} | {d['ticker']:<10} | Actual: {d['actual']:>10.4f} | From TX: {d['calculated']:>10.4f} | Diff: {d['difference']:>10.4f}")
        if len(discrepancies) > 20:
            print(f"    ... and {len(discrepancies) - 20} more discrepancies")
    else:
        print("\n  ✅ All holdings match calculated positions from transactions!")
    
    session.close()
    
    print("\n" + "=" * 70)
    print("✅ INGESTION COMPLETE")
    print("=" * 70)
    
    return True


def run_ingestion(resume: bool = False):
    """Run the full ingestion process."""
    print("=" * 70)
    print("🚀 WARROOM INITIAL INGESTION")
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Check for resume
    checkpoint = load_checkpoint()
    start_step = 1
    
    if resume and checkpoint['last_completed_step'] > 0:
        start_step = checkpoint['last_completed_step'] + 1
        print(f"\n📌 Resuming from step {start_step} (last completed: {checkpoint['last_completed_step']})")
    elif not resume:
        clear_checkpoint()
    
    # Run each step
    for step in INGESTION_STEPS:
        if step['id'] < start_step:
            print(f"\n⏭️  Step {step['id']}: {step['description']} (skipped - already completed)")
            continue
        
        print(f"\n{'='*70}")
        print(f"📌 Step {step['id']}/{len(INGESTION_STEPS)}: {step['description']}")
        print("=" * 70)
        
        success = False
        
        if step['name'] == 'clear_database':
            success = clear_database()
        elif step['name'] == 'reconciliation':
            success = generate_reconciliation_report()
        elif 'script' in step:
            success = run_parser_script(step['script'])
        else:
            print(f"  ⚠️  Unknown step: {step['name']}")
            success = False
        
        if success:
            save_checkpoint(step['id'])
            print(f"\n  ✅ Step {step['id']} completed successfully")
        else:
            print(f"\n  ❌ Step {step['id']} FAILED")
            print(f"\n  💡 To resume from this step, run: python initial_ingestion.py --resume")
            return False
    
    # Clear checkpoint on successful completion
    clear_checkpoint()
    
    print("\n" + "=" * 70)
    print("🎉 ALL INGESTION STEPS COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Warroom Initial Ingestion')
    parser.add_argument('--resume', action='store_true', help='Resume from last checkpoint')
    parser.add_argument('--step', type=int, help='Run only a specific step')
    
    args = parser.parse_args()
    
    if args.step:
        # Run specific step
        step = next((s for s in INGESTION_STEPS if s['id'] == args.step), None)
        if step:
            print(f"Running step {args.step}: {step['description']}")
            if 'script' in step:
                run_parser_script(step['script'])
            elif step['name'] == 'clear_database':
                clear_database()
            elif step['name'] == 'reconciliation':
                generate_reconciliation_report()
        else:
            print(f"Step {args.step} not found")
    else:
        run_ingestion(resume=args.resume)
