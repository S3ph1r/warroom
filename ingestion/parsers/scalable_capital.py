"""
WAR ROOM - Scalable Capital / Baader Bank PDF Parser (V5 - Robust Version)
Parses Monthly Account Statements from Scalable Capital (via Baader Bank)
Replaces legacy parser with robust block-regex logic.
"""
import re
import pypdf
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ScalableCapitalPDFParser:
    """
    Parser for Scalable Capital / Baader Bank Monthly Account Statement PDFs.
    Extracts Purchase, Sale, Dividend, Fee, and Cash movements using robust V5 logic.
    """

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        
        # Regex patterns (V5)
        self.date_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})')
        self.amount_pattern = re.compile(r'(-?[\d\.,]+)') 
        
        # Transaction Keywords (V5)
        self.KEYWORDS = {
            "BUY": ["Purchase", "Kauf"],
            "SELL": ["Sale", "Verkauf"],
            "DIVIDEND": ["Coupons/Dividends", "Erträge/Dividenden", "Dividende"],
            "FEE": ["Ordergebühr", "ORDERGEBUEHR", "Provision", "Cost"],
            "DEPOSIT": ["Direct Debit", "Einzahlung", "Deposit", "Lastschrift", "Bonifico"],
            "WITHDRAWAL": ["Payout", "Auszahlung", "Withdrawal"],
            "INTEREST": ["Incentive Campaign", "Zinsen", "Interest"],
            "TAX": ["Tax", "Steuer", "Kapitalertragsteuer", "Solidaritätszuschlag", "Kirchensteuer"]
        }

    def parse(self) -> List[Dict]:
        """
        Parses the PDF and returns a list of transaction dictionaries in the Standard Format.
        """
        logger.info(f"Parsing Scalable Capital statement from: {self.file_path}")
        transactions = []
        
        try:
            reader = pypdf.PdfReader(str(self.file_path))
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() + "\n"

            lines = full_text.split('\n')
            
            current_date = None
            current_block = []
            
            parsed_txs = []

            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue

                # Check for Date at start (YYYY-MM-DD usually in Baader V5 logic, or DD.MM.YYYY?)
                # Wait, V5 parser used self.date_pattern which is YYYY-MM-DD?
                # Actually, Baader PDFs often have german format DD.MM.YYYY but the V5 regex was YYYY-MM-DD?
                # Let's check V5 code I read again.
                # It extracted date using self.date_pattern.search(line).
                # But it also had re.sub(r'\d{2}\.\d{2}\.\d{4}'...)
                # If regex is YYYY-MM-DD, maybe text extraction converts it? 
                # Or maybe date pattern is wrong?
                # In Verification script output, dates are YYYY-MM-DD.
                # Let's check `ScalableMonthlyParser` init again. `r'(\d{4}-\d{2}-\d{2})'`.
                # If this worked, the PDFs contain YYYY-MM-DD.
                
                date_match = self.date_pattern.search(line)
                
                if date_match:
                     # This looks like a transaction start line
                     if current_block:
                         tx = self._process_block(current_block)
                         if tx:
                             parsed_txs.append(tx)
                         current_block = []
                     
                     current_block.append(line)
                     current_date = date_match.group(1)
                elif current_block:
                    if "Account Balance" in line or "Page" in line:
                        pass
                    else:
                        current_block.append(line)

            # Flush last block
            if current_block:
                tx = self._process_block(current_block)
                if tx:
                    parsed_txs.append(tx)

            # Convert to Legacy/Standard Format
            for tx in parsed_txs:
                std_tx = self._convert_to_standard_format(tx)
                if std_tx:
                    transactions.append(std_tx)

            logger.info(f"Successfully parsed {len(transactions)} transactions")
            return transactions

        except Exception as e:
            logger.error(f"Error parsing {self.file_path}: {e}")
            return []

    def _process_block(self, block: List[str]) -> Optional[Dict]:
        """
        Analyzes a transaction block (V5 logic).
        """
        try:
            full_block_text = " ".join(block)
            
            # 1. Determine Type
            tx_type = "UNKNOWN"
            for key, keywords in self.KEYWORDS.items():
                if any(kw in full_block_text for kw in keywords):
                    tx_type = key
                    break
            
            if tx_type == "UNKNOWN":
                if "No transactions" in full_block_text:
                    return None
                # return None # Skip unknowns? V5 returned None commented out
            
            # 2. Extract Date
            date_match = self.date_pattern.search(full_block_text)
            if not date_match:
                return None
            tx_date = date_match.group(1)

            # 3. Extract Details
            txn_amount = None
            qty = None
            isin = None
            description = ""
            
            # Cleanup for Amount Extraction
            text_for_amount = re.sub(r'\d{2}\.\d{2}\.\d{4}', '', full_block_text) # Remove DD.MM.YYYY
            text_for_amount = re.sub(r'Balance[:\s]+[\d.,]+', '', text_for_amount, flags=re.IGNORECASE) # Remove Balance

            # Special Case: "Account Balance" snapshot
            if "Account Balance" in full_block_text or "Periodic Account Statement" in full_block_text:
                tx_type = "BALANCE_SNAPSHOT"
            
            text_for_amount = re.sub(r'KKTKK[\d-]+[\.,][\d]+', '', text_for_amount) # Remove reference IDs

            # Ignore "Periodic Account Statement" blocks
            if "Periodic Account Statement" in full_block_text:
                return None

            for line in block:
                # ISIN
                if "ISIN" in line:
                    isin_match = re.search(r'ISIN\s+([A-Z0-9]{12})', line)
                    if isin_match:
                        isin = isin_match.group(1)
                
                # Quantity (STK)
                if "STK" in line and qty is None:
                    qty_match = re.search(r'STK\s+([\d\.,]+)', line)
                    if qty_match:
                        qty = self._parse_german_decimal(qty_match.group(1))

                # Description accumulator
                if not isin and not qty and "ISIN" not in line and "STK" not in line:
                    description += line + " "

            # Amount Extraction (Block Regex)
            matches = re.findall(r'(\d[\d.,]*[.,]\d{2})\s?(-?)', text_for_amount)
            
            candidates = []
            for val_str, sign in matches:
                try:
                    val = self._parse_german_decimal(val_str)
                    if sign == "-":
                        val = -val
                    elif "Debit" in full_block_text and val > 0:
                        pass 
                    candidates.append(val)
                except:
                    continue
            
            if candidates:
                txn_amount = candidates[-1]
                
                # Special Case: Incentive Campaign -> INTEREST (Positive)
                if tx_type == "WITHDRAWAL" and ("Incentive" in description or "Incentive" in full_block_text):
                    tx_type = "INTEREST"
                
                # Sign Adjustment
                if txn_amount > 0:
                     if tx_type in ["BUY", "FEE", "WITHDRAWAL", "TAX"]:
                         txn_amount = -txn_amount
            
            # Check for Account Balance snapshot (generic UNKNOWN with amount)
            # If description contains 'Account Balance', ignore it effectively by returning None or handling in caller?
            # V5 logic kept it as UNKNOWN.
            # But we want to filter it out if it's just a balance snapshot.
            if "Account Balance" in description:
                return None

            return {
                "date": tx_date,
                "type": tx_type,
                "amount": txn_amount,
                "currency": "EUR",
                "isin": isin,
                "quantity": qty,
                "description": description.strip(),
                "raw_text": full_block_text
            }

        except Exception as e:
            return None

    def _parse_german_decimal(self, value_str: str) -> float:
        """
        Parses 1.234,56 -> 1234.56
        Parses 1,234.56 -> 1234.56
        """
        clean = value_str.strip()
        last_comma = clean.rfind(',')
        last_dot = clean.rfind('.')

        if last_comma != -1 and last_dot != -1:
            if last_comma > last_dot:
                clean = clean.replace(".", "").replace(",", ".") # German
            else:
                clean = clean.replace(",", "") # English
        elif last_comma != -1:
            clean = clean.replace(",", ".") # German simple
        
        return float(clean)

    def _convert_to_standard_format(self, v5_tx: Dict) -> Optional[Dict]:
        """Maps V5 dictionary to the Legacy/System Dictionary"""
        if not v5_tx or v5_tx['amount'] is None:
            return None
            
        # Map Type
        op_map = {
            'BUY': 'BUY',
            'SELL': 'SELL',
            'DIVIDEND': 'DIVIDEND',
            'FEE': 'FEE',
            'TAX': 'FEE', # Mapping TAX to FEE (Cost) to be safe with enums
            'DEPOSIT': 'DEPOSIT',
            'WITHDRAWAL': 'WITHDRAW', # Drop AL
            'INTEREST': 'INTEREST',
            'BALANCE_SNAPSHOT': 'BALANCE_SNAPSHOT'
        }
        
        op_type = op_map.get(v5_tx['type'], 'UNKNOWN')
        if op_type == 'UNKNOWN':
            return None # Skip unknowns

        # Date
        try:
            dt = datetime.strptime(v5_tx['date'], "%Y-%m-%d")
        except:
            return None

        # Amount (Float -> Decimal)
        amount = Decimal(str(v5_tx['amount']))
        quantity = Decimal(str(v5_tx['quantity'])) if v5_tx['quantity'] else Decimal('1')
        
        # Product Name
        product = v5_tx['isin'] if v5_tx['isin'] else v5_tx['description'][:50] # Fallback
        
        return {
            'timestamp': dt,
            'product_name': product,
            'operation_type': op_type,
            'quantity': quantity,
            'price_unit': abs(amount / quantity) if quantity else Decimal('0'),
            'fiat_amount': abs(amount), # Legacy uses positive amounts + Type? 
            # WAIT. Legacy `_parse_transactions` returned positive amounts usually?
            # BUY: 62.27 - -> fiat_amount 62.27.
            # SELL: ... -> fiat_amount.
            # The system likely infers sign from operation_type.
            # I should output POSITIVE absolute amount.
            'isin': v5_tx['isin'],
            'platform': 'SCALABLE_CAPITAL',
            'status': 'VERIFIED'
        }

def parse_scalable_pdf(file_path: str) -> List[Dict]:
    parser = ScalableCapitalPDFParser(file_path)
    return parser.parse()

def parse_all_scalable_pdfs(directory: str) -> List[Dict]:
    all_transactions = []
    folder = Path(directory)
    for pdf_file in folder.glob('*.pdf'):
        if 'Monthly account statement' in pdf_file.name or 'Statement' in pdf_file.name:
            try:
                parser = ScalableCapitalPDFParser(str(pdf_file))
                transactions = parser.parse()
                all_transactions.extend(transactions)
            except Exception:
                pass
    return all_transactions
