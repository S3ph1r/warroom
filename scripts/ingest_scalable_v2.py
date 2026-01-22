"""
Scalable Capital (Baader Bank) Ingestion Script - V4 (Modular)
Strategy: Specialized Parsers for each Document Type + Snapshot Reconciliation.
"""
import uuid
import sys
import re
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict
from pypdf import PdfReader
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import SessionLocal
from db.models import Holding, Transaction, ImportLog

# Configuration
BROKER = "SCALABLE_CAPITAL"
INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def parse_german_date(date_str: str) -> Optional[datetime]:
    """Parse date like '2024-11-05', '15.11.2022', or '02.01.2026'"""
    date_str = date_str.strip()
    if not date_str: return None
    # Try ISO
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        pass
    # Try German/Italian
    try:
        return datetime.strptime(date_str, "%d.%m.%Y")
    except ValueError:
        return None

def parse_amount(num_str: str) -> Decimal:
    """Parse Amount from PDF string handling German/US formats."""
    s = num_str.strip().replace("EUR", "").replace("USD", "").strip()
    if not s or s == "-": return Decimal(0)
    
    try:
        # Standardize: remove thousands separators, keep decimal point
        if ',' in s and '.' in s:
            if s.rfind(',') > s.rfind('.'): # German 1.234,56
                s = s.replace('.', '').replace(',', '.')
            else: # US 1,234.56
                s = s.replace(',', '')
        elif ',' in s:
            # Heuristic: if comma is near the end (2-3 digits), assume decimal
            # But Baader often uses '.' for decimals in English files.
            # In Italian/German files ',' is decimal.
            # Let's check trailing digits
            parts = s.split(',')
            if len(parts[-1]) <= 2:
                s = s.replace('.', '').replace(',', '.')
            else: # Thousand separator
                s = s.replace(',', '')
        return Decimal(s)
    except:
        return Decimal(0)

def extract_asset_metadata(raw_name: str) -> dict:
    """Extract metadata from raw asset name."""
    metadata = {
        'clean_name': raw_name,
        'share_class': None,
        'adr_ratio': None,
        'nominal_value': None,
        'market': None
    }
    if not raw_name: return metadata
    name = raw_name.strip()
    
    # Extract market code
    market_match = re.search(r'\b(DK|YC|US|UK|DE|FR|JP|HK|CN)\b(?:\s+[\d,\.]+)?$', name)
    if market_match:
        metadata['market'] = market_match.group(1).upper()
        name = name[:market_match.start()].strip()
    
    # Extract share class
    class_match = re.search(r'\b(CL\.[AB]|AS\s+[AB]|CLASS\s+[AB]|REG\.SHS H|REG\. SHARES|REGISTERED SHARES)\b', name, re.I)
    if class_match:
        metadata['share_class'] = class_match.group(1).upper()
        name = name.replace(class_match.group(0), '').strip()
    
    # Extract ADR ratio
    adr_match = re.search(r'(?:ADR\s*/\s*(\d+)|(\d+)\s*/\s*(\d+))', name, re.I)
    if adr_match:
        if adr_match.group(1): metadata['adr_ratio'] = float(adr_match.group(1))
        elif adr_match.group(2) and adr_match.group(3):
            metadata['adr_ratio'] = float(adr_match.group(2)) / float(adr_match.group(3))
        name = re.sub(r'(?:ADR\s*/\s*\d+|\d+\s*/\s*\d+)', '', name, flags=re.I).strip()
    
    # Extract nominal value
    nominal_match = re.search(r'(DL|HD|YC|DK)\s*[-\s]*([0-9,\.]+)', name, re.I)
    if nominal_match:
        value_str = nominal_match.group(2).replace(',', '.')
        if '.' not in value_str: value_str = '0.' + value_str.lstrip('0') or '0'
        metadata['nominal_value'] = value_str
        name = name.replace(nominal_match.group(0), '').strip()
    
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'\s*[,\-\.]+\s*$', '', name).strip()
    metadata['clean_name'] = name
    return metadata

def determine_asset_type(name: str, isin: str) -> str:
    """
    Determine if asset is STOCK, ETF, or CASH based on name/ISIN.
    """
    if not name and not isin: return "STOCK"
    
    name_upper = name.upper() if name else ""
    isin_upper = isin.upper() if isin else ""
    
    # 1. Keywords for ETFs
    if "ETF" in name_upper or "UCITS" in name_upper or "XTRACKERS" in name_upper or "ISHARES" in name_upper or "VANGUARD" in name_upper or "AMUNDI" in name_upper:
        return "ETF"
    
    # 2. ISIN Prefixes common for European ETFs
    if isin_upper.startswith("IE") or isin_upper.startswith("LU"):
        # Most IE/LU assets in Scalable are ETFs (some exceptions like Spotify LU, but rare)
        # Check against known stocks if needed, but safe default for Scalable users
        if "SPOTIFY" in name_upper: return "STOCK"
        return "ETF"
        
    return "STOCK"

# Import Price Service for Smart Resolution
from services.price_service_v5 import resolve_asset_info

# --- PARSER 1: Baader Monthly Statement (English) ---
def parse_baader_monthly_statement(pdf_path: Path) -> List[Transaction]:
    txs = []
    try:
        reader = PdfReader(pdf_path)
        text = "\n".join([p.extract_text() for p in reader.pages])
        lines = text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            op = None
            if line == "Purchase" or line == "Savings Plan": op = "BUY"
            elif line == "Sale": op = "SELL"
            elif line in ["Coupons/Dividends", "Dividends"]: op = "DIVIDEND"
            
            if op:
                tx_date = None
                for k in range(1, 5):
                    if i-k >= 0:
                        d = parse_german_date(lines[i-k])
                        if d: tx_date = d; break
                
                amount = Decimal(0)
                if i+1 < len(lines):
                    possible_amt = lines[i+1].strip()
                    if re.match(r'^[\d\.,\s]+$', possible_amt):
                        amount = parse_amount(possible_amt)
                
                isin, qty, name = None, Decimal(0), "Unknown"
                for k in range(1, 10):
                    if i+k >= len(lines): break
                    sub = lines[i+k].strip()
                    if sub in ["Purchase", "Sale", "Savings Plan", "Dividends"]: break
                    if sub.startswith("ISIN"):
                        parts = sub.split()
                        if len(parts) >= 2: isin = parts[1]; name = lines[i+k-1].strip()
                    if sub.startswith("STK"):
                        m = re.search(r'STK\s+([\d\.,]+)', sub)
                        if m: qty = parse_amount(m.group(1))
                
                if isin or (op == "DIVIDEND" and amount > 0):
                    # Smart Resolution
                    resolved = resolve_asset_info(isin, name)
                    final_ticker = resolved.get('ticker') or name[:20]
                    final_name = resolved.get('name') or name
                    asset_type = determine_asset_type(final_name, isin)

                    meta = extract_asset_metadata(name)
                    txs.append(Transaction(
                        id=uuid.uuid4(), broker=BROKER, ticker=final_ticker, isin=isin,
                        operation=op, status="COMPLETED", quantity=qty, 
                        price= (amount/qty) if qty > 0 else Decimal(0),
                        total_amount=amount, currency="EUR", timestamp=tx_date or datetime.now(),
                        source_document=pdf_path.name, **{k:v for k,v in meta.items() if k != 'clean_name'}
                    ))
            i += 1
    except Exception as e: logger.error(f"Error {pdf_path.name}: {e}")
    return txs

# --- PARSER 2: Scalable Monthly Statement (Italian/New Format) ---
def parse_scalable_monthly_statement(pdf_path: Path) -> List[Transaction]:
    txs = []
    try:
        reader = PdfReader(pdf_path)
        text = "\n".join([p.extract_text() for p in reader.pages])
        lines = text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # Triggers: "Bonifico", "Distribuzioni", "Commissione", or the pz. line
            # "06.12.2025 06.12.2025 Bonifico +15.65 EUR"
            # "29.12.2025 30.12.2025 Distribuzioni di azioni societarie iShares... +0.18 EUR"
            # "pz. Baidu A (KYG070341048) -84.38 EUR"
            
            if "pz." in line:
                # This is a purchase/sale. 
                # E.g., "1.0 pz. Baidu A (KYG070341048) -84.38 EUR"
                match = re.search(r'([\d\.,]+)\s+pz\.\s+(.*?)\s+\((.*?)\)\s+([-\d\.,]+)\s+EUR', line)
                if match:
                    qty = parse_amount(match.group(1))
                    name = match.group(2)
                    isin = match.group(3)
                    total = parse_amount(match.group(4))
                    op = "BUY" if total < 0 else "SELL" # In statement, negative means cash out = Buy stock
                    
                    tx_date = None
                    if i > 0:
                        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', lines[i-1])
                        if date_match: tx_date = parse_german_date(date_match.group(1))
                    
                    meta = extract_asset_metadata(name)
                    
                    # Smart Resolution
                    resolved = resolve_asset_info(isin, name)
                    final_ticker = resolved.get('ticker') or meta['clean_name'][:20]
                    final_name = resolved.get('name') or meta['clean_name']
                    asset_type = determine_asset_type(final_name, isin)
                    
                    txs.append(Transaction(
                        id=uuid.uuid4(), broker=BROKER, ticker=final_ticker, isin=isin,
                        operation=op, status="COMPLETED", quantity=qty,
                        price=abs(total/qty) if qty > 0 else 0, total_amount=abs(total),
                        currency="EUR", timestamp=tx_date or datetime.now(),
                        source_document=pdf_path.name, **{k:v for k,v in meta.items() if k != 'clean_name'}
                    ))
            elif "Distribuzioni" in line:
                # "29.12.2025 30.12.2025 Distribuzioni di azioni societarie"
                # "iShares MSCI Brazil (Dist) (IE00B0M63516) +0.18 EUR"
                if i+1 < len(lines):
                    next_line = lines[i+1].strip()
                    match = re.search(r'(.*?)\s+\((.*?)\)\s+\+?([\d\.,]+)\s+EUR', next_line)
                    if match:
                        name, isin, total = match.group(1), match.group(2), parse_amount(match.group(3))
                        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', line)
                        tx_date = parse_german_date(date_match.group(1)) if date_match else datetime.now()
                        meta = extract_asset_metadata(name)
                        txs.append(Transaction(
                            id=uuid.uuid4(), broker=BROKER, ticker=meta['clean_name'][:20], isin=isin,
                            operation="DIVIDEND", status="COMPLETED", quantity=0, price=0,
                            total_amount=total, currency="EUR", timestamp=tx_date,
                            source_document=pdf_path.name, **{k:v for k,v in meta.items() if k != 'clean_name'}
                        ))
            i += 1
    except Exception as e: logger.error(f"Error {pdf_path.name}: {e}")
    return txs

# --- PARSER 3: Corporate Actions (Splits) ---
def parse_corporate_actions(pdf_path: Path) -> List[Transaction]:
    txs = []
    try:
        reader = PdfReader(pdf_path)
        text = "\n".join([p.extract_text() for p in reader.pages])
        if "Split" in text:
            # "Split ... Units 12 ... ISIN: US05606L1008"
            # "Ratio: 1 : 6"
            isin_match = re.search(r'ISIN:\s+([A-Z0-9]{12})', text)
            ratio_match = re.search(r'Ratio:\s+(\d+)\s+:\s+(\d+)', text)
            date_match = re.search(r'as of (\d{4}-\d{2}-\d{2})', text)
            qty_match = re.search(r'Entry into sec\. account.*?Units\s+(\d+)', text, re.S)
            
            if isin_match and ratio_match:
                isin = isin_match.group(1)
                from_ratio, to_ratio = int(ratio_match.group(1)), int(ratio_match.group(2))
                qty = Decimal(qty_match.group(1)) if qty_match else Decimal(0)
                tx_date = parse_german_date(date_match.group(1)) if date_match else datetime.now()
                
                # We create a special "SPLIT" transaction. 
                # Our current model lacks SPLIT op, so we use a huge COMMENT or adjust qty.
                # Actually, for the Portfolio engine, a BUY of the DIFFERENCE or a total reset works.
                # Let's mark it as BUY with 0 price to adjust the quantity.
                # Since Split is 1:6, we had 2, now 12. We add 10.
                diff_qty = qty - (qty * from_ratio / to_ratio)
                txs.append(Transaction(
                    id=uuid.uuid4(), broker=BROKER, ticker=f"SPLIT {isin}", isin=isin,
                    operation="BUY", status="COMPLETED", quantity=diff_qty, price=0,
                    total_amount=0, currency="EUR", timestamp=tx_date,
                    source_document=pdf_path.name
                ))
    except Exception as e: logger.error(f"Error {pdf_path.name}: {e}")
    return txs

# --- PARSER 4: Baader Income Statement ---
def parse_baader_income_statement(pdf_path: Path) -> List[Transaction]:
    # Placeholder for the existing implementation in v2, slightly improved
    txs = []
    try:
        reader = PdfReader(pdf_path)
        text = "\n".join([p.extract_text() for p in reader.pages])
        lines = text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if "Dividend payment" in line or "Investment fund income distribution" in line:
                isin, total, name, qty, tx_date = None, Decimal(0), "Unknown", Decimal(0), None
                for k in range(1, 15):
                    if i+k >= len(lines): break
                    sub = lines[i+k].strip()
                    if sub.startswith("ISIN:"): isin = sub.split(":")[1].split("/")[0].strip()
                    if "Accrual:" in sub: tx_date = parse_german_date(sub.split(":")[1].split("/")[0].strip())
                    if "Gross amount" in lines[i+k-1] and not total: total = parse_amount(sub)
                    if "Nominal Value/Unit" in sub and i+k+1 < len(lines): qty = parse_amount(lines[i+k+1])
                    if isin and name == "Unknown" and re.search(r'[A-Z]', sub) and len(sub) > 5: name = sub
                if isin and total > 0:
                    meta = extract_asset_metadata(name)
                    txs.append(Transaction(
                        id=uuid.uuid4(), broker=BROKER, ticker=meta['clean_name'][:20], isin=isin,
                        operation="DIVIDEND", status="COMPLETED", quantity=qty, price=0,
                        total_amount=total, currency="EUR", timestamp=tx_date or datetime.now(),
                        source_document=pdf_path.name, **{k:v for k,v in meta.items() if k != 'clean_name'}
                    ))
            elif "Disposal" in line: # SELL in Income Statement
                isin, qty, name, tx_date = None, Decimal(0), "Unknown", None
                for k in range(1, 20):
                    if i+k >= len(lines): break
                    sub = lines[i+k].strip()
                    if sub.startswith("ISIN:"): isin = sub.split(":")[1].split("/")[0].strip()
                    if "Value Date" in sub: tx_date = parse_german_date(sub.split(":")[1].split("/")[0].strip())
                    if "Nominal Value" in sub and i+k+1 < len(lines): qty = parse_amount(lines[i+k+1])
                    if isin and name == "Unknown" and not any(x in sub for x in ["ISIN", "Value", "Unit"]): name = sub
                if isin and qty > 0:
                    meta = extract_asset_metadata(name)
                    txs.append(Transaction(
                        id=uuid.uuid4(), broker=BROKER, ticker=meta['clean_name'][:20], isin=isin,
                        operation="SELL", status="COMPLETED", quantity=qty, price=0,
                        total_amount=0, currency="EUR", timestamp=tx_date or datetime.now(),
                        source_document=pdf_path.name, **{k:v for k,v in meta.items() if k != 'clean_name'}
                    ))
            i += 1
    except Exception as e: logger.error(f"Error {pdf_path.name}: {e}")
    return txs

# --- PARSER 5: Snapshot Parser (Securities Statement) ---
def parse_holdings_snapshot(pdf_path: Path) -> Dict[str, Decimal]:
    """Returns {isin: quantity} from a snapshot file."""
    holdings = {}
    try:
        reader = PdfReader(pdf_path)
        text = "\n".join([p.extract_text() for p in reader.pages])
        # Format: "120.0 Xiaomi ... KYG9830T1067"
        # Or: "Quantity Description ... ISIN: ..."
        lines = text.split('\n')
        for i, line in enumerate(lines):
            # Regex for "Qty Name ... ISIN"
            match = re.search(r'^(\d+[\d\.,]*)\s+(.*?)\s+([A-Z0-9]{12})', line)
            if match:
                holdings[match.group(3)] = parse_amount(match.group(1))
            else:
                # Variant: ISIN on next line
                match_qty = re.search(r'^(\d+[\d\.,]*)\s+(.*)', line)
                if match_qty and i+1 < len(lines) and re.match(r'^[A-Z0-9]{12}$', lines[i+1].strip()):
                    holdings[lines[i+1].strip()] = parse_amount(match_qty.group(1))
    except Exception as e: logger.error(f"Error {pdf_path.name}: {e}")
    return holdings

def ingest_scalable():
    print("🚀 SCALABLE V4: MODULAR INGESTION & SNAPSHOT ALIGNMENT")
    session = SessionLocal()
    try:
        # 1. Routing & Parsing
        all_files = list(INBOX.glob("*.pdf"))
        all_txs = []
        snapshots = []
        
        for p in sorted(all_files):
            name = p.name
            if "Corporate actions" in name: all_txs.extend(parse_corporate_actions(p))
            elif "Income statement" in name: all_txs.extend(parse_baader_income_statement(p))
            elif "Monthly account statement Baader Bank" in name: all_txs.extend(parse_baader_monthly_statement(p))
            elif "Monthly account statement Broker Scalable Capital" in name: all_txs.extend(parse_scalable_monthly_statement(p))
            elif "Securities account statement" in name or "Account statement Baader Bank" in name:
                snapshots.append(p)
        
        # 2. Deduplication
        unique_txs, seen = [], set()
        for t in all_txs:
            sig = (t.timestamp.date(), t.operation, t.isin, float(t.quantity), float(t.total_amount))
            if sig not in seen:
                seen.add(sig); unique_txs.append(t)
        
        # 3. Apply Snapshot (Baseline)
        # Find latest snapshot
        latest_snapshot_file = max(snapshots, key=lambda x: x.name) if snapshots else None
        official_holdings = parse_holdings_snapshot(latest_snapshot_file) if latest_snapshot_file else {}
        
        # 4. Save Transactions
        session.query(Transaction).filter(Transaction.broker == BROKER).delete()
        session.add_all(unique_txs)
        session.commit()
        
        # 5. Calculate & Reconcile Holdings
        current_holdings = {} # ISIN -> info
        for tx in sorted(unique_txs, key=lambda x: x.timestamp):
            isin = tx.isin
            if not isin: continue
            if isin not in current_holdings: 
                current_holdings[isin] = {'qty': Decimal(0), 'cost': Decimal(0), 'meta': tx}
            
            if tx.operation == "BUY":
                current_holdings[isin]['qty'] += tx.quantity
                current_holdings[isin]['cost'] += tx.total_amount
            elif tx.operation == "SELL":
                current_holdings[isin]['qty'] -= tx.quantity
                if current_holdings[isin]['qty'] > 0:
                    avg = current_holdings[isin]['cost'] / (current_holdings[isin]['qty'] + tx.quantity)
                    current_holdings[isin]['cost'] -= (avg * tx.quantity)
                else: current_holdings[isin]['cost'] = 0
        
        # RECONCILIATION: Fix discrepancies using Snapshot
        holdings_to_save = []
        for isin, off_qty in official_holdings.items():
            calc = current_holdings.get(isin, {'qty': 0, 'cost': 0, 'meta': None})
            if calc['qty'] != off_qty:
                logger.warning(f"⚖️ Reconciliation: {isin} Calculated={calc['qty']}, Snapshot={off_qty}. Fixing to Snapshot.")
                calc['qty'] = off_qty
            
            # Use metadata from snapshot asset (if we had any trans) or placeholder
            meta = calc['meta']
            
            # Smart Resolution for Holdings too!
            resolved = resolve_asset_info(isin, meta.ticker if meta else isin)
            final_ticker = resolved.get('ticker') or (meta.ticker if meta else isin[:10])
            final_name = resolved.get('name') or (meta.ticker if meta else isin)
            # Re-determine asset type (snapshot implies ownership, check ISIN)
            asset_type = determine_asset_type(final_name, isin)
            
            holdings_to_save.append(Holding(
                id=uuid.uuid4(), broker=BROKER, ticker=final_ticker,
                isin=isin, name=final_name, asset_type=asset_type,
                quantity=off_qty, purchase_price=(calc['cost']/off_qty) if off_qty > 0 else 0,
                current_value=0, currency="EUR", source_document=latest_snapshot_file.name,
                last_updated=datetime.now(), share_class=meta.share_class if meta else None,
                adr_ratio=meta.adr_ratio if meta else None, nominal_value=meta.nominal_value if meta else None,
                market=meta.market if meta else None
            ))
            
        session.query(Holding).filter(Holding.broker == BROKER).delete()
        session.add_all(holdings_to_save)
        session.commit()
        
        print(f"✅ Extracted {len(unique_txs)} transactions and {len(holdings_to_save)} holdings.")

    except Exception as e:
        session.rollback(); logger.error(f"Global Error: {e}")
    finally: session.close()

if __name__ == "__main__":
    ingest_scalable()
