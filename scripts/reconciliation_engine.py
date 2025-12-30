import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Paths
DATA_DIR = Path(__file__).resolve().parent.parent / 'data' / 'extracted'
FINAL_DIR = Path(__file__).resolve().parent.parent / 'data' / 'clean'
FINAL_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def load_extracted_data(broker_name):
    """
    Loads all JSONs for a broker and separates them into Holdings and Transactions.
    """
    broker_dir = DATA_DIR / broker_name
    if not broker_dir.exists():
        logger.error(f"Directory not found: {broker_dir}")
        return [], []

    holdings = []
    transactions = []

    for f in broker_dir.glob("*.json"):
        try:
            with open(f, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                
                # Check document type
                # Some files might be lists wrapped in dict, or just lists
                # The extractors return { "data": [...], "document_type": "..." }
                
                doc_type = data.get("document_type", "UNKNOWN")
                items = data.get("data", [])
                
                # If extractors created generic lists without wrapper (legacy), try to guess
                # But our new extractors use the wrapper
                
                if doc_type == "HOLDING" or doc_type == "HOLDINGS":
                    holdings.extend(items)
                elif doc_type == "TRANSACTIONS" or doc_type == "TRANSACTION":
                    transactions.extend(items)
                else:
                    # Fallback heuristic: check fields
                    if items and 'quantity' in items[0]:
                        if 'date' in items[0] and ('type' in items[0] or 'Type' in items[0]):
                             transactions.extend(items)
                        else:
                             holdings.extend(items)
        except Exception as e:
            logger.error(f"Error loading {f.name}: {e}")

    return holdings, transactions

def normalize_ticker(ticker):
    """
    Normalize ticker strings (trim, uppercase).
    Future: Mapping table.
    """
    if not ticker: return "UNKNOWN"
    return str(ticker).strip().upper()

def reconcile_broker(broker_name):
    logger.info(f"⚖️ RECONCILIATION STARTED: {broker_name}")
    
    # 1. Load Data
    holdings_list, transactions_list = load_extracted_data(broker_name)
    logger.info(f"   Loaded {len(holdings_list)} Holdings targets.")
    logger.info(f"   Loaded {len(transactions_list)} Transactions history.")
    
    if not holdings_list:
        logger.warning(f"   No holdings found for {broker_name}. Skipping reconciliation.")
        return

def safe_float(val):
    if val is None: return 0.0
    if isinstance(val, (int, float)): return float(val)
    try:
        # Handle "1.234,56" vs "1,234.56"
        # Simple heuristic: remove thousands sep, fix decimal
        s = str(val).strip().replace('EUR','').replace('USD','').strip()
        if ',' in s and '.' in s:
            # Ambiguous. Assume last one is decimal if logic allows, or just standard replace
            pass 
        return float(s.replace(',', '.')) 
    except:
        return 0.0

def reconcile_broker(broker_name):
    logger.info(f"⚖️ RECONCILIATION STARTED: {broker_name}")
    
    # 1. Load Data
    holdings_list, transactions_list = load_extracted_data(broker_name)
    logger.info(f"   Loaded {len(holdings_list)} Holdings targets.")
    logger.info(f"   Loaded {len(transactions_list)} Transactions history.")
    
    if not holdings_list:
        logger.warning(f"   No holdings found for {broker_name}. Skipping reconciliation.")
        return

    # 2. Build Target Map {Ticker: Quantity} and {Ticker: ISIN}
    target_map = {}
    ticker_isin_map = {}
    
    for h in holdings_list:
        tick = normalize_ticker(h.get('ticker', ''))
        
        # Fix: CSV extracted json might have keys lowercase.
        # Check quantity key variants
        raw_qty = h.get('quantity') or h.get('Quantity') or h.get('Quantità')
        qty = safe_float(raw_qty)
        
        # Capture ISIN
        isin = h.get('isin') or h.get('ISIN')
        if isin and len(isin) > 5: # Basic valid check
             ticker_isin_map[tick] = isin
        
        target_map[tick] = target_map.get(tick, 0) + qty

    # 3. Process Transactions
    tx_by_ticker = {}
    global_min_date = "2099-12-31"
    clean_transactions = []

    for tx in transactions_list:
        tick = normalize_ticker(tx.get('ticker', ''))
        
        raw_qty = tx.get('quantity')
        qty = safe_float(raw_qty)
        
        op_type = tx.get('type', 'BUY').upper()
        
        # Adjust sign if needed based on type
        if "SELL" in op_type or "VENDITA" in op_type:
             if qty > 0: qty = -qty
        elif "BUY" in op_type or "ACQUISTO" in op_type:
             if qty < 0: qty = abs(qty) # Force positive for buy
        
        # Store standardized tx
        std_tx = tx.copy()
        std_tx['quantity'] = qty
        std_tx['ticker'] = tick
        std_tx['broker'] = broker_name
        
        # Inject ISIN if missing in Tx but present in Holding
        current_isin = std_tx.get('isin')
        if not current_isin or len(current_isin) < 5:
            if tick in ticker_isin_map:
                std_tx['isin'] = ticker_isin_map[tick]
        
        # Date tracking
        d = tx.get('date', '2099-12-31')
        if d < global_min_date: global_min_date = d
        
        clean_transactions.append(std_tx)
        
        # Sum for reconciliation
        if op_type in ['BUY', 'SELL', 'DEPOSIT', 'WITHDRAW', 'TRANSFER']:
            tx_by_ticker[tick] = tx_by_ticker.get(tick, 0) + qty

    # 4. Reconciliation Loop
    final_history = list(clean_transactions)
    
    # Calculate synthetic date (Oldest - 1 day)
    try:
        dt = datetime.strptime(global_min_date, "%Y-%m-%d")
        synthetic_date = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
    except:
        synthetic_date = "2020-01-01" # Default if date parsing fails

    logger.info(f"   Reconciliation Date: {synthetic_date}")

    for ticker, target_qty in target_map.items():
        hist_qty = tx_by_ticker.get(ticker, 0)
        diff = target_qty - hist_qty
        
        if abs(diff) > 0.000001: # Float epsilon
            logger.info(f"   🔧 Fixing {ticker}: Target={target_qty}, History={hist_qty}, Diff={diff}")
            
            # Create SYNTHETIC TRANSACTION
            rec_tx = {
                "date": synthetic_date,
                "type": "RECONCILIATION", # Special tag
                "ticker": ticker,
                "isin": ticker_isin_map.get(ticker), # INJECT ISIN
                "quantity": diff,
                "price": 0.0,
                "total_amount": 0.0,
                "currency": "EUR", # Default? Or infer from holding?
                "broker": broker_name,
                "notes": "Generated by WarRoom Reconciliation Engine"
            }
            final_history.append(rec_tx)
        else:
            # logger.info(f"   ✅ {ticker} matches.")
            pass

    # 5. Save Global Clean History for Broker
    out_file = FINAL_DIR / f"{broker_name}_history.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(final_history, f, indent=2)

    logger.info(f"✅ Saved {out_file.name} with {len(final_history)} records.")

if __name__ == "__main__":
    # Test run
    reconcile_broker("bgsaxo")
