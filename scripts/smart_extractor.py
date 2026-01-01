"""
Smart Extractor - Phase 3 of Ingestion Pipeline

Goal: Transform "Classified Candidates" (from Phase 2) into normalized transaction rows.
Output: A list of dicts matching the 'Transaction' schema, saved to 'extraction_results.json'.

Features:
- Excel/CSV Extraction: Deterministic, using column mappings from Phase 2.
- PDF Extraction: Sequential Vision analysis (All Pages).
- Normalization: Dates, Numbers, Currencies.
- Asset Handling: Stocks, Crypto, Commodities (XAU/XAG), Cash.
"""

import sys
import json
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
import re
import requests
import json
import re

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# ============================================================
# UTILITIES (Inlined to avoid dependency hell)
# ============================================================
def clean_json_text(text: str) -> str:
    """Clean markdown code blocks from JSON string."""
    text = text.strip()
    
    # Pattern to find content inside ```json ... ``` or ``` ... ```
    # Dotall to capture newlines
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if match:
         return match.group(1).strip()
         
    return text.strip()

def parse_with_retry(text: str) -> dict:
    """Robust JSON parsing."""
    try:
        clean = clean_json_text(text)
        return json.loads(clean)
    except json.JSONDecodeError:
        # Try to find { ... } subset
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except:
                pass
        return {}
        
VISION_MODEL = "llama3.2-vision:11b"
TEXT_MODEL = "qwen2.5:14b"

def call_text_ollama(prompt: str, model: str = TEXT_MODEL) -> str:
    """Call Ollama with Text model (Qwen)."""
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "30m",
        "options": {"temperature": 0.0, "num_ctx": 4096}
    }
    try:
        resp = requests.post(url, json=payload, timeout=300)
        if resp.status_code == 200:
            return resp.json().get("response", "")
    except:
        pass
    return ""

def call_vision_ollama(prompt: str, images: list, model: str = VISION_MODEL) -> str:
    """Call Ollama with vision model (Inlined for Extractor)."""
    url = "http://localhost:11434/api/generate"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "images": images,
        "stream": False,
        "keep_alive": "30m", 
        "options": {
            "temperature": 0.0,
            "num_predict": 1000, # Longer for extraction
            "num_ctx": 4096
        }
    }
    
    try:
        # Increase timeout drastically for extraction (10 min)
        resp = requests.post(url, json=payload, timeout=600)
        
        if resp.status_code == 200:
            result = resp.json().get("response", "")
            return result
        else:
            return ""
    except Exception as e:
        return ""

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("warroom_ingestion.log", mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger("SmartExtractor")


class SmartExtractor:
    def __init__(self, orchestration_file: Path):
        self.orchestration_file = orchestration_file
        self.results = []
        self.extraction_errors = []

    def run(self):
        """Main execution loop."""
        logger.info("="*60)
        logger.info("🏭 SMART EXTRACTOR - Phase 3")
        logger.info("="*60)

        if not self.orchestration_file.exists():
            logger.error(f"Orchestration file not found: {self.orchestration_file}")
            return

        with open(self.orchestration_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        processed_files = data.get("processed", [])
        logger.info(f"Found {len(processed_files)} files to extract.")

        for file_info in processed_files:
            try:
                self._process_file(file_info)
            except Exception as e:
                logger.error(f"❌ Critical error processing {file_info.get('file')}: {e}")
                self.extraction_errors.append({"file": file_info.get('file'), "error": str(e)})

        self._save_results()

    def _process_file(self, file_info: dict):
        """Route to appropriate extractor based on file type."""
        filepath = Path(file_info["file"])
        broker = file_info["broker"]
        doc_type = file_info["document_type"]
        is_pdf = file_info.get("is_pdf", False)
        
        logger.info(f"\n📂 [{broker}] {filepath.name} ({doc_type})")

        extracted_rows = []
        
        if is_pdf:
            extracted_rows = self._extract_from_pdf(filepath, file_info)
        else:
            extracted_rows = self._extract_from_excel(filepath, file_info)
            
        if extracted_rows:
            logger.info(f"   ✅ Extracted {len(extracted_rows)} rows.")
            # Normalize and append
            for row in extracted_rows:
                norm_row = self._normalize_row(row, file_info)
                if norm_row:
                    self.results.append(norm_row)
        else:
            logger.warning("   ⚠️ No rows extracted.")

    # ============================================================
    # EXCEL / CSV STRATEGY
    # ============================================================
    def _extract_from_excel(self, filepath: Path, file_info: dict) -> list:
        """Deterministic extraction using pandas and Phase 2 column mapping."""
        mapping = file_info["classification"]["column_mapping"]
        if not mapping:
            logger.warning("   ⚠️ No column mapping available for Excel file.")
            return []

        # Expected headers from mapping (values)
        expected_headers = [v for k, v in mapping.items() if v]
        
        # Load with Auto-Header Detection
        df = self._read_excel_auto_header(filepath, expected_headers)
        
        if df is None or df.empty:
            logger.warning(f"   ⚠️ Could not load Excel table (Headers not found: {expected_headers})")
            return []

        # Fix Single Column Issue (CSV in Excel)
        if len(df.columns) == 1 and isinstance(df.columns[0], str) and (',' in df.columns[0] or ';' in df.columns[0]):
            logger.info("   ⚠️ Detected single column with delimiters. Attempting to split...")
            # Use current column name as header line to split
            header_str = df.columns[0]
            delim = ',' if ',' in header_str else ';'
            
            # Split the index (header)
            new_columns = [h.strip() for h in header_str.split(delim)]
            
            # Split the data
            current_col = df.columns[0]
            split_data = df[current_col].astype(str).str.split(delim, expand=True)
            
            # Assign new columns (trimming mismatch)
            if split_data.shape[1] == len(new_columns):
                split_data.columns = new_columns
                df = split_data
            else:
                 # Mismatch in columns, try to just use new columns up to shape
                 logger.warning(f"   ⚠️ Split shape mismatch: {split_data.shape[1]} vs {len(new_columns)} headers")
                 # Try minimal fix
                 split_data.columns = [f"Col_{i}" for i in range(split_data.shape[1])]
                 # Try to map what we can
                 for i, col in enumerate(new_columns):
                     if i < len(split_data.columns):
                         split_data = split_data.rename(columns={split_data.columns[i]: col})
                 df = split_data

        # DEBUG: Log found columns
        logger.info(f"   🔍 Found Columns: {list(df.columns)}")
        
        # Create reverse mapping (CSV Header -> Standard Field)
        col_map = {v: k for k, v in mapping.items() if v}
        logger.info(f"   🗺️ Mapping: {col_map}")
        
        # Normalize headers (strip whitespace)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Filter only mapped columns
        mapped_df = df.rename(columns=col_map)
        logger.info(f"   ➡️ Mapped Columns: {list(mapped_df.columns)}")
        
        # Keep only columns that match our standard keys
        standard_keys = ['date', 'symbol', 'operation_type', 'quantity', 'price', 'total_amount', 'fees', 'currency', 'balance']
        available_keys = [k for k in standard_keys if k in mapped_df.columns]
        logger.info(f"   ✅ Available Keys: {available_keys}")
        
        # Convert to list of dicts
        raw_rows = mapped_df[available_keys].to_dict('records')
        
        # Pre-filter empty rows (must have at least date and amount/qty)
        valid_rows = []
        for row in raw_rows:
            # Check mandatory fields existence (values checked in normalization)
            if 'date' in row and ('total_amount' in row or 'quantity' in row or 'price' in row):
                valid_rows.append(row)
                
        return valid_rows

    def _read_excel_auto_header(self, filepath: Path, expected_cols: list) -> pd.DataFrame:
        """Scan first 20 rows to find header."""
        try:
            # Read first few rows as header-less
            if filepath.suffix.lower() == '.csv':
                # For CSV, assume header is row 0 usually, but safer to check
                preview = pd.read_csv(filepath, nrows=20, header=None)
            else:
                preview = pd.read_excel(filepath, nrows=20, header=None)
            
            # Find row with most matches
            best_idx = -1
            max_matches = 0
            
            # Normalize expected
            expected_set = set(str(c).lower().strip() for c in expected_cols)
            
            for idx, row in preview.iterrows():
                # Convert row to string set
                row_vals = set(str(val).lower().strip() for val in row.values)
                matches = len(row_vals.intersection(expected_set))
                
                if matches > max_matches and matches >= len(expected_cols) * 0.5: # At least 50% match
                    max_matches = matches
                    best_idx = idx
            
            if best_idx != -1:
                # Reload with correct header
                if filepath.suffix.lower() == '.csv':
                    return pd.read_csv(filepath, header=best_idx)
                else:
                    return pd.read_excel(filepath, header=best_idx)
            
            # Fallback: Read normally (Row 0)
            if filepath.suffix.lower() == '.csv':
                return pd.read_csv(filepath)
            else:
                return pd.read_excel(filepath)
                
        except Exception as e:
            logger.error(f"   ❌ Header detection failed: {e}")
            return None

    # ============================================================
    # PDF VISION STRATEGY
    # ============================================================
    def _extract_from_pdf(self, filepath: Path, file_info: dict) -> list:
        """Hydrid PDF Extraction: Respects Phase 2 Strategy."""
        strategy = file_info.get("classification", {}).get("extraction_strategy", "TEXT_LLM")
        logger.info(f"   🧠 Extraction Strategy: {strategy}")
        
        # 1. FORCE VISION if requested
        if strategy == "VISION_LLM":
             logger.info(f"   👁️ Strategy is VISION. Skipping text check.")
             images = self._pdf_to_all_images(filepath)
             if not images: return []
             # ... continue to vision loop ... provided by helper or fall through?
             # To keep code clean, I will move Vision Loop to _extract_from_pdf_vision
             return self._extract_from_pdf_vision(filepath, file_info)

        # 2. Try Text Extraction (Native PDF)
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(filepath))
            text_content = ""
            for page in reader.pages:
                text_content += page.extract_text() + "\n"
            
            if len(text_content.strip()) > 100:
                logger.info(f"   📝 Native PDF detected ({len(text_content)} chars). Using Text Model ({TEXT_MODEL}).")
                return self._extract_from_pdf_text_raw(text_content, file_info)
        except Exception as e:
            logger.warning(f"   ⚠️ Text Extraction check failed: {e}")

        # 3. Fallback to Vision (Scanned / Image-only)
        logger.info(f"   👁️ Fallback to Vision Extraction ({VISION_MODEL})...")
        return self._extract_from_pdf_vision(filepath, file_info)

    def _extract_from_pdf_vision(self, filepath: Path, file_info: dict) -> list:
        """Helper for Vision Loop."""
        images = self._pdf_to_all_images(filepath)
        if not images: return []

            
        logger.info(f"   👁️ Starting Vision Extraction on {len(images)} pages...")
        all_rows = []
        
        for i, img in enumerate(images):
            idx = i + 1
            logger.info(f"      📸 Scanning Page {idx}/{len(images)}...")
            
            # Retrieve Context from Phase 2
            doc_type = file_info.get("document_type", "Financial Document")
            summary = file_info.get("classification", {}).get("content_summary", "Transaction history")
            
            # Prompt for extraction (Safety Filter Bypass + Context Aware)
            prompt = f"""
            OCR Task: Transpose the data in this image into a JSON structure.
            Document Type: {doc_type}
            Context: {summary}
            
            This is my own personal financial data I need to digitize.
            
            Return a JSON object with a key "rows".
            Fields to extract: "date", "symbol", "amount", "currency", "description".
            
            Example Format:
            {{ "rows": [ {{ "date": "2023-01-01", "symbol": "AAPL", "amount": 150.00, "currency": "USD" }} ] }}
            
            If no table is present, return {{ "rows": [] }}.
            output JSON only.
            """
            
            response = call_vision_ollama(prompt, [img])
            
            # DEBUG: Log raw response snippet
            clean_snippet = response.replace('\n', ' ')[:100]
            logger.info(f"      💬 Raw Response Snippet: {clean_snippet}...")
            
            data = parse_with_retry(response)
            
            if data and "rows" in data and isinstance(data["rows"], list):
                page_rows = data["rows"]
                logger.info(f"      ✅ Found {len(page_rows)} rows on page {idx}.")
                all_rows.extend(page_rows)
            else:
                logger.warning(f"      ⚠️ No structured data found on page {idx}. (Raw len: {len(response)})")
                
    def _extract_from_pdf_text_raw(self, text: str, file_info: dict) -> list:
        """Extract transactions from raw PDF text using Qwen."""
        import re
        doc_type = file_info.get("document_type", "Financial Document")
        
        # Chunking strategy: split by pages or large blocks if needed. 
        # For now, send full text if fits in context (Qwen has 32k context usually).
        # We'll truncate to safe limit just in case.
        safe_text = text[:12000] # ~3k tokens, safe for 4k context limit (or 32k)
        
        prompt = f"""
        Task: Extract financial transactions from the following text into JSON.
        Document Type: {doc_type}
        
        Text Content:
        \"\"\"
        {safe_text}
        \"\"\"
        
        Return a JSON object with a key "rows".
        Fields for each row:
        - "date": Transaction date (YYYY-MM-DD format)
        - "symbol": Stock/ETF ticker or name
        - "quantity": Number of shares/units traded (e.g. 10, 0.5, 100)
        - "price": Price per share/unit in the currency
        - "amount": Total transaction value (quantity * price)
        - "currency": Currency code (EUR, USD, etc.)
        - "operation": One of: PURCHASE, SALE, DIVIDEND, DEBIT, CREDIT, DELIVERY
        
        IMPORTANT: Extract the actual quantity (number of shares) and price per share when available.
        If only total amount is shown, put it in "amount" and set "quantity" to 1.
        
        Example:
        {{ "rows": [ {{ "date": "2023-01-01", "symbol": "AAPL", "quantity": 10, "price": 150.00, "amount": 1500.00, "currency": "USD", "operation": "PURCHASE" }} ] }}
        
        Strictly output valid JSON. If no transactions found, return {{ "rows": [] }}.
        """
        
        response = call_text_ollama(prompt)
        # Debug Log
        snippet = response.replace('\n', ' ')[:100]
        logger.info(f"      💬 Text Model Response: {snippet}...")
        
        data = parse_with_retry(response)
        if data and "rows" in data:
            return data["rows"]
        else:
            logger.warning(f"      ⚠️ No structured data found in text.")
            return []

    def _pdf_to_all_images(self, filepath: Path) -> list:
        """Convert ALL pages of a PDF to base64 images."""
        from pdf2image import convert_from_path, pdfinfo_from_path
        import io
        import base64
        
        # Poppler path for Windows (same as smart_classifier)
        poppler_path = project_root / "tools" / "poppler-24.02.0" / "Library" / "bin"
        poppler_arg = str(poppler_path) if poppler_path.exists() else None
        
        try:
            images = convert_from_path(str(filepath), dpi=150, poppler_path=poppler_arg) # Increased DPI
            base64_images = []
            
            for img in images:
                # Resize for Vision (2000x2000 max) -> HIGHER RESOLUTION
                img.thumbnail((2000, 2000))
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                base64_images.append(b64)
                
            return base64_images
        except Exception as e:
            logger.error(f"   ❌ PDF Conversion failed: {e}")
            return []

    # ============================================================
    # NORMALIZATION
    # ============================================================
    
    # Universal Operation Mapping (Broker-Agnostic)
    OPERATION_MAP = {
        # English
        "SALE": "SELL", "SOLD": "SELL", "SELL": "SELL",
        "PURCHASE": "BUY", "BUY": "BUY", "BOUGHT": "BUY",
        "DIVIDEND": "DIVIDEND", "DIV": "DIVIDEND", "COUPON": "DIVIDEND",
        "FEE": "FEE", "DEBIT": "FEE", "ORDERGEBUEHR": "FEE", "COMMISSION": "FEE",
        "DEPOSIT": "DEPOSIT", "CREDIT": "DEPOSIT", "TOP-UP": "DEPOSIT",
        "WITHDRAW": "WITHDRAW", "WITHDRAWAL": "WITHDRAW",
        "DELIVERY": "TRANSFER_IN", "TRANSFER": "TRANSFER_IN",
        "INTEREST": "INTEREST",
        # Italian
        "ACQUISTO": "BUY", "VENDITA": "SELL", "DIVIDENDO": "DIVIDEND",
        "RICARICA": "DEPOSIT", "PRELIEVO": "WITHDRAW"
    }
    
    def _normalize_row(self, row: dict, file_info: dict) -> dict:
        """Clean and validate data into Standard Transaction Format."""
        try:
            # 0. UNIVERSAL POST-PROCESSING: Parse raw_data if present
            # LLM often returns structured data inside a 'raw_data' string
            raw_data_str = row.get("raw_data", "")
            if raw_data_str and isinstance(raw_data_str, str):
                try:
                    # Parse the Python dict string (e.g. "{'date': '2024-01-01', ...}")
                    import ast
                    parsed = ast.literal_eval(raw_data_str)
                    if isinstance(parsed, dict):
                        # Merge parsed data into row (parsed takes priority for empty fields)
                        for k, v in parsed.items():
                            if k not in row or row.get(k) in [None, "", 0, 0.0, "UNKNOWN"]:
                                row[k] = v
                except:
                    pass  # If parsing fails, continue with original row
            
            # 1. Date Parsing
            raw_date = row.get('date')
            if pd.isna(raw_date) or not raw_date: return None
            
            clean_date = self._parse_date(raw_date)
            if not clean_date: return None
            
            # 2. Number Parsing (European vs US)
            clean_qty = self._parse_number(row.get('quantity'))
            clean_price = self._parse_number(row.get('price'))
            clean_amount = self._parse_number(row.get('amount') or row.get('total_amount'))
            clean_fees = self._parse_number(row.get('fees'))
            
            # 3. Symbol / Description
            symbol = str(row.get('symbol', '')).strip()
            description = str(row.get('operation_type', '') or row.get('description', '')).strip()
            
            # 4. OPERATION NORMALIZATION (Universal)
            raw_op = str(row.get('operation', '')).strip().upper()
            normalized_op = self.OPERATION_MAP.get(raw_op, None)
            if not normalized_op:
                # Fallback: Try to infer from description
                normalized_op = self._infer_operation(description, clean_qty, clean_amount)
            
            # 5. Asset Type Override
            asset_type = file_info.get('asset_type', 'UNKNOWN')
            
            # CASH HANDLING
            if asset_type == 'CASH':
                if not symbol or symbol.lower() == 'nan':
                    curr = str(row.get('currency', '')).strip()
                    symbol = curr if curr else 'EUR'
                
            # COMMODITY HANDLING
            if asset_type == 'COMMODITY':
                if 'gold' in symbol.lower() or 'xau' in symbol.lower() or 'oro' in symbol.lower():
                    symbol = 'XAU'
                if 'silver' in symbol.lower() or 'xag' in symbol.lower() or 'argento' in symbol.lower():
                    symbol = 'XAG'

            # 6. Output Construction
            return {
                "broker": file_info["broker"],
                "date": clean_date.isoformat(),
                "symbol": symbol,
                "description": description,
                "operation": normalized_op,
                "quantity": float(clean_qty) if clean_qty else 0.0,
                "price": float(clean_price) if clean_price else 0.0,
                "amount": float(clean_amount) if clean_amount else 0.0,
                "fees": float(clean_fees) if clean_fees else 0.0,
                "currency": str(row.get('currency', 'EUR')).strip(),
                "asset_type": asset_type,
                "source_file": Path(file_info["file"]).name,
                "raw_data": str(row)  # For debugging/lineage
            }
            
        except Exception as e:
            # logger.warning(f"Row normalization failed: {e} | Row: {row}")
            return None

    def _parse_date(self, val):
        try:
            return pd.to_datetime(val).date()
        except:
            return None

    def _parse_number(self, val):
        if pd.isna(val) or val is None: return 0.0
        if isinstance(val, (int, float)): return float(val)
        
        s = str(val).strip()
        # Remove currency symbols AND text codes (e.g. USD, EUR)
        # Keep digits, minus, comma, dot
        s = re.sub(r'[^\d.,-]', '', s).strip()
        
        if not s: 
            return 0.0
            
        # Heuristic for 1.000,00 (EU) vs 1,000.00 (US)
        if ',' in s and '.' in s:
            if s.find(',') > s.find('.'): # 1.000,00 -> EU
                 s = s.replace('.', '').replace(',', '.')
            else: # 1,000.00 -> US
                 s = s.replace(',', '')
        elif ',' in s: # 1000,00 -> EU
             s = s.replace(',', '.')
             
        try:
            return float(s)
        except:
            return 0.0

    def _infer_operation(self, desc, qty, amount):
        """Infer BUY/SELL/DIVIDEND from description or signs."""
        d = desc.lower()
        if 'buy' in d or 'purchase' in d or 'acquisto' in d: return 'BUY'
        if 'sell' in d or 'sold' in d or 'vendita' in d: return 'SELL'
        if 'div' in d or 'dividend' in d: return 'DIVIDEND'
        if 'dep' in d or 'top-up' in d or 'ricarica' in d: return 'DEPOSIT'
        if 'fee' in d or 'cost' in d: return 'FEE'
        if 'interest' in d: return 'INTEREST'
        
        # Fallback to sign
        if qty and qty > 0: return 'BUY' # Usually positive qty = you gained asset
        if qty and qty < 0: return 'SELL'
        if amount and amount > 0: return 'DEPOSIT' # ? Context dependent
        
        return 'UNKNOWN'

    def _save_results(self):
        output_file = project_root / "extraction_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"\n💾 Extraction saved to: {output_file} ({len(self.results)} total rows)")


if __name__ == "__main__":
    extractor = SmartExtractor(project_root / "orchestration_results.json")
    # extractor = SmartExtractor(project_root / "orchestration_force_pdf.json") # FORCE TEST
    extractor.run()
