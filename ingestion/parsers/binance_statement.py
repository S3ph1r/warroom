"""
WAR ROOM - Binance Account Statement PDF Parser
Parses Account Statement PDF exports for current holdings snapshot
"""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Optional
from pathlib import Path
from loguru import logger

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


class BinanceAccountStatementParser:
    """
    Parser for Binance Account Statement PDF exports.
    These PDFs contain a snapshot of current holdings with values.
    
    Contains:
    - Total Account Value
    - Spot & Margin holdings
    - Earn holdings (staking)
    - Funding holdings
    - Asset allocation with quantities and USD values
    """
    
    def __init__(self, file_path: str, password: str = None):
        self.file_path = Path(file_path)
        self.password = password or "66666666"  # Default password
        self.holdings = []
        self.summary = {}
        
    def parse(self) -> Dict:
        """Parse the Account Statement PDF"""
        if not fitz:
            raise ImportError("PyMuPDF (fitz) is required for PDF parsing")
        
        logger.info(f"Parsing Binance Account Statement: {self.file_path}")
        
        pdf = fitz.open(str(self.file_path))
        
        # Authenticate if encrypted
        if pdf.is_encrypted:
            if not pdf.authenticate(self.password):
                raise ValueError("Invalid PDF password")
        
        # Extract all text
        full_text = ""
        for page in pdf:
            full_text += page.get_text() + "\n"
        
        pdf.close()
        
        # Parse summary
        self._parse_summary(full_text)
        
        # Parse holdings from consolidated summary
        self._parse_consolidated_holdings(full_text)
        
        # Parse Spot holdings
        self._parse_spot_holdings(full_text)
        
        # Parse Earn holdings
        self._parse_earn_holdings(full_text)
        
        logger.info(f"Parsed {len(self.holdings)} holdings, total: ${self.summary.get('total_value_usd', 0):,.2f}")
        
        return {
            'summary': self.summary,
            'holdings': self.holdings
        }
    
    def _parse_summary(self, text: str):
        """Extract summary information"""
        # Total Account Value
        match = re.search(r'Total Account Value\n([\d,]+\.?\d*)\s*USD', text)
        if match:
            self.summary['total_value_usd'] = self._parse_number(match.group(1))
        
        # Report date
        match = re.search(r'Report Date\n(\d{4}/\d{2}/\d{2})', text)
        if match:
            self.summary['report_date'] = datetime.strptime(match.group(1), '%Y/%m/%d')
        
        # Report period
        match = re.search(r'Report Period\n([A-Za-z]+ \d+, \d+) - ([A-Za-z]+ \d+, \d+)', text)
        if match:
            self.summary['period_start'] = match.group(1)
            self.summary['period_end'] = match.group(2)
        
        # Account ID
        match = re.search(r'Account ID:\n?(\d+)', text)
        if match:
            self.summary['account_id'] = match.group(1)
        
        # Wallet balances
        match = re.search(r'Spot & Margin\n([\d,]+\.?\d*)\s*USD', text)
        if match:
            self.summary['spot_margin_usd'] = self._parse_number(match.group(1))
            
        match = re.search(r'Earn\n([\d,]+\.?\d*)\s*USD', text)
        if match:
            self.summary['earn_usd'] = self._parse_number(match.group(1))
    
    def _parse_consolidated_holdings(self, text: str):
        """Parse consolidated top 10 assets from page 2"""
        # Pattern: SYMBOL Name\nQuantity\nPrice\nValue
        # Example: BNB BNB\n1.326349 1.326344 / 0.000005\n$843.070000...\n$1,118.21...
        
        holdings_section = re.search(
            r'Your Consolidated Top 10 Assets.*?(?=CONSOLIDATED|FUNDING|$)',
            text, re.DOTALL
        )
        
        if not holdings_section:
            return
        
        section_text = holdings_section.group(0)
        
        # Parse each asset line
        # Symbol line followed by quantity/price/value lines
        lines = section_text.split('\n')
        
        i = 0
        while i < len(lines) - 3:
            line = lines[i].strip()
            
            # Check if this looks like a symbol line (SYMBOL name)
            symbol_match = re.match(r'^([A-Z]+)\s+(.+)$', line)
            if symbol_match:
                symbol = symbol_match.group(1)
                name = symbol_match.group(2)
                
                # Next lines should contain quantity, price, value
                quantity_line = lines[i+1] if i+1 < len(lines) else ''
                price_line = lines[i+2] if i+2 < len(lines) else ''
                value_line = lines[i+3] if i+3 < len(lines) else ''
                
                # Extract current quantity (first number)
                qty_match = re.search(r'^([\d.]+)', quantity_line)
                quantity = self._parse_number(qty_match.group(1)) if qty_match else Decimal('0')
                
                # Extract current price
                price_match = re.search(r'\$([\d,.]+)', price_line)
                price = self._parse_number(price_match.group(1)) if price_match else Decimal('0')
                
                # Extract current value
                value_match = re.search(r'\$([\d,.]+)', value_line)
                value = self._parse_number(value_match.group(1)) if value_match else Decimal('0')
                
                if quantity > 0:
                    self.holdings.append({
                        'symbol': symbol,
                        'name': name,
                        'quantity': float(quantity),
                        'price_usd': float(price),
                        'value_usd': float(value),
                        'wallet': 'CONSOLIDATED',
                        'platform': 'BINANCE',
                    })
                
                i += 4
            else:
                i += 1
    
    def _parse_spot_holdings(self, text: str):
        """Parse Spot wallet holdings"""
        spot_section = re.search(
            r'Spot Top 10 Holdings.*?(?=Margin Top 10|FUTURES|OPTION|EARN|$)',
            text, re.DOTALL
        )
        
        if spot_section:
            self._parse_holding_section(spot_section.group(0), 'SPOT')
    
    def _parse_earn_holdings(self, text: str):
        """Parse Earn wallet holdings"""
        earn_section = re.search(
            r'Earn Top 10 Holdings.*?(?=FUNDING|$)',
            text, re.DOTALL
        )
        
        if earn_section:
            self._parse_holding_section(earn_section.group(0), 'EARN')
    
    def _parse_holding_section(self, section_text: str, wallet: str):
        """Generic parser for a holdings section"""
        lines = section_text.split('\n')
        
        i = 0
        while i < len(lines) - 3:
            line = lines[i].strip()
            
            symbol_match = re.match(r'^([A-Z]+)\s+(.+)$', line)
            if symbol_match and len(symbol_match.group(1)) <= 10:
                symbol = symbol_match.group(1)
                name = symbol_match.group(2)
                
                # Check if already in holdings from consolidated
                existing = next((h for h in self.holdings if h['symbol'] == symbol), None)
                if existing:
                    existing['wallet'] = wallet  # Update wallet info
                    i += 4
                    continue
                
                quantity_line = lines[i+1] if i+1 < len(lines) else ''
                value_line = lines[i+3] if i+3 < len(lines) else ''
                
                qty_match = re.search(r'^([\d.]+)', quantity_line)
                quantity = self._parse_number(qty_match.group(1)) if qty_match else Decimal('0')
                
                value_match = re.search(r'\$([\d,.]+)', value_line)
                value = self._parse_number(value_match.group(1)) if value_match else Decimal('0')
                
                price = value / quantity if quantity > 0 else Decimal('0')
                
                if quantity > 0:
                    self.holdings.append({
                        'symbol': symbol,
                        'name': name,
                        'quantity': float(quantity),
                        'price_usd': float(price),
                        'value_usd': float(value),
                        'wallet': wallet,
                        'platform': 'BINANCE',
                    })
                
                i += 4
            else:
                i += 1
    
    def _parse_number(self, value: str) -> Decimal:
        """Parse number from string"""
        if not value:
            return Decimal('0')
        
        value_str = str(value).strip().replace(',', '').replace('$', '')
        
        try:
            return Decimal(value_str)
        except InvalidOperation:
            return Decimal('0')
    
    def get_total_value_usd(self) -> float:
        """Get total portfolio value in USD"""
        return float(self.summary.get('total_value_usd', 0))
    
    def get_holdings_df(self):
        """Return holdings as pandas DataFrame"""
        import pandas as pd
        return pd.DataFrame(self.holdings)


def parse_binance_account_statement(file_path: str, password: str = None) -> Dict:
    """Convenience function to parse Binance Account Statement PDF"""
    parser = BinanceAccountStatementParser(file_path, password)
    return parser.parse()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = r"D:\Download\Binance\AccountStatementPeriod_10773818_20251216-20251217_d9522f326b11499f84f5e85f77195e60.pdf"
    
    parser = BinanceAccountStatementParser(file_path)
    result = parser.parse()
    
    print(f"\n📊 BINANCE ACCOUNT STATEMENT")
    print("=" * 60)
    print(f"Report Date: {result['summary'].get('report_date')}")
    print(f"Total Value: ${result['summary'].get('total_value_usd', 0):,.2f} USD")
    print(f"  Spot & Margin: ${result['summary'].get('spot_margin_usd', 0):,.2f}")
    print(f"  Earn: ${result['summary'].get('earn_usd', 0):,.2f}")
    
    print(f"\n📈 HOLDINGS ({len(result['holdings'])} assets)")
    print("-" * 60)
    for h in sorted(result['holdings'], key=lambda x: x['value_usd'], reverse=True):
        print(f"  {h['symbol']:8} | Qty: {h['quantity']:>14.6f} | ${h['value_usd']:>10,.2f}")
    
    total_from_holdings = sum(h['value_usd'] for h in result['holdings'])
    print(f"\n  {'TOTAL':8} | {'':>20} | ${total_from_holdings:>10,.2f}")
