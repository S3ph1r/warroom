"""
Inbox Scanner Service
Scans the inbox folder for new broker files and triggers import.
"""
import os
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InboxScanner:
    """
    Scans inbox folders for new broker files and manages import workflow.
    """
    
    # Broker configurations: folder name -> (file patterns, parser function)
    BROKER_CONFIG = {
        'bgsaxo': {
            'patterns': ['Posizioni_*.csv'],
            'parser': 'parse_bgsaxo_positions',
            'description': 'BG Saxo Positions CSV'
        },
        'scalable': {
            'patterns': ['*Financial status*.pdf', '*Financial Status*.pdf'],
            'parser': 'parse_scalable_status',
            'description': 'Scalable Capital Financial Status'
        },
        'binance': {
            'patterns': ['AccountStatementPeriod_*.pdf'],
            'parser': 'parse_binance_statement',
            'description': 'Binance Account Statement'
        },
        'revolut': {
            'patterns': ['trading-account-statement_*.pdf'],
            'parser': 'parse_revolut_trading',
            'description': 'Revolut Trading Statement'
        },
        'traderepublic': {
            'patterns': ['*.png', '*.jpg', 'Screenshot*.png'],
            'parser': 'manual_entry_required',
            'description': 'Trade Republic (Screenshot)'
        },
        'ibkr': {
            'patterns': ['*.TRANSACTIONS.*.csv', 'ActivityStatement*.csv'],
            'parser': 'parse_ibkr_csv',
            'description': 'IBKR Activity Statement'
        }
    }
    
    def __init__(self, inbox_path: str, processed_path: str):
        """
        Initialize scanner with inbox and processed paths.
        
        Args:
            inbox_path: Root path to inbox folder (e.g., G:/My Drive/WAR_ROOM_DATA/inbox)
            processed_path: Root path to processed folder
        """
        self.inbox_path = Path(inbox_path)
        self.processed_path = Path(processed_path)
        self.import_log_path = self.inbox_path.parent / 'logs' / 'import_log.json'
        
        # Create directories if they don't exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create required directories if they don't exist."""
        # Create inbox subdirectories
        for broker in self.BROKER_CONFIG.keys():
            (self.inbox_path / broker).mkdir(parents=True, exist_ok=True)
            (self.processed_path / broker).mkdir(parents=True, exist_ok=True)
        
        # Create logs directory
        self.import_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def scan_inbox(self) -> Dict[str, List[Path]]:
        """
        Scan inbox for new files by broker.
        
        Returns:
            Dict mapping broker name to list of new file paths
        """
        results = {}
        
        for broker, config in self.BROKER_CONFIG.items():
            broker_inbox = self.inbox_path / broker
            if not broker_inbox.exists():
                continue
            
            # Find matching files
            files = []
            for pattern in config['patterns']:
                files.extend(broker_inbox.glob(pattern))
            
            if files:
                results[broker] = sorted(files, key=lambda f: f.stat().st_mtime)
                logger.info(f"Found {len(files)} new file(s) for {broker}")
        
        return results
    
    def get_inbox_status(self) -> Dict[str, dict]:
        """
        Get status of inbox for each broker.
        
        Returns:
            Dict with broker status info
        """
        status = {}
        pending_files = self.scan_inbox()
        import_log = self._load_import_log()
        
        for broker, config in self.BROKER_CONFIG.items():
            broker_status = {
                'broker': broker,
                'description': config['description'],
                'pending_files': len(pending_files.get(broker, [])),
                'pending_file_names': [f.name for f in pending_files.get(broker, [])],
                'last_import': import_log.get(broker, {}).get('last_import'),
                'last_file': import_log.get(broker, {}).get('last_file'),
                'status': 'ok'
            }
            
            # Calculate status based on last import
            if broker_status['last_import']:
                last_import = datetime.fromisoformat(broker_status['last_import'])
                days_since = (datetime.now() - last_import).days
                
                if days_since > 14:
                    broker_status['status'] = 'alert'
                elif days_since > 7:
                    broker_status['status'] = 'warning'
            else:
                broker_status['status'] = 'never_imported'
            
            status[broker] = broker_status
        
        return status
    
    def import_file(self, broker: str, file_path: Path) -> dict:
        """
        Import a single file for a broker.
        
        Args:
            broker: Broker name
            file_path: Path to file to import
            
        Returns:
            Import result dict
        """
        result = {
            'broker': broker,
            'file': file_path.name,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'message': '',
            'records_imported': 0
        }
        
        config = self.BROKER_CONFIG.get(broker)
        if not config:
            result['message'] = f'Unknown broker: {broker}'
            return result
        
        parser_name = config['parser']
        
        # Handle manual entry brokers
        if parser_name == 'manual_entry_required':
            result['message'] = 'This broker requires manual data entry from screenshot'
            result['success'] = True
            return result
        
        try:
            # Import the appropriate parser and run it
            records = self._run_parser(parser_name, file_path)
            result['records_imported'] = records
            result['success'] = True
            result['message'] = f'Successfully imported {records} records'
            
            # Move file to processed
            self._move_to_processed(broker, file_path)
            
            # Update import log
            self._update_import_log(broker, file_path.name, records)
            
        except Exception as e:
            result['message'] = f'Import failed: {str(e)}'
            logger.error(f"Import failed for {broker}/{file_path.name}: {e}")
        
        return result
    
    def import_all_pending(self) -> List[dict]:
        """
        Import all pending files from inbox.
        
        Returns:
            List of import results
        """
        results = []
        pending = self.scan_inbox()
        
        for broker, files in pending.items():
            for file_path in files:
                result = self.import_file(broker, file_path)
                results.append(result)
        
        return results
    
    def _run_parser(self, parser_name: str, file_path: Path) -> int:
        """
        Run the appropriate parser for a file.
        
        Returns:
            Number of records imported
        """
        # Parser implementations - delegated to specific parsers
        # For now, return placeholder
        logger.info(f"Running parser {parser_name} on {file_path}")
        
        # TODO: Integrate with actual parsers
        # from ingestion.parsers import bgsaxo, scalable, binance, revolut, ibkr
        
        return 0  # Placeholder
    
    def _move_to_processed(self, broker: str, file_path: Path):
        """Move imported file to processed folder."""
        dest_dir = self.processed_path / broker
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Add timestamp to filename to avoid conflicts
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_name = f"{timestamp}_{file_path.name}"
        dest_path = dest_dir / new_name
        
        shutil.move(str(file_path), str(dest_path))
        logger.info(f"Moved {file_path.name} to {dest_path}")
    
    def _load_import_log(self) -> dict:
        """Load import log from JSON file."""
        if self.import_log_path.exists():
            with open(self.import_log_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _update_import_log(self, broker: str, filename: str, records: int):
        """Update import log with new import."""
        log = self._load_import_log()
        
        log[broker] = {
            'last_import': datetime.now().isoformat(),
            'last_file': filename,
            'records_imported': records
        }
        
        with open(self.import_log_path, 'w') as f:
            json.dump(log, f, indent=2)
    
    def print_status(self):
        """Print formatted status of all brokers."""
        status = self.get_inbox_status()
        
        print("=" * 60)
        print("📥 INBOX STATUS")
        print("=" * 60)
        
        for broker, info in status.items():
            status_icon = {
                'ok': '🟢',
                'warning': '🟡',
                'alert': '🔴',
                'never_imported': '⚪'
            }.get(info['status'], '❓')
            
            pending = info['pending_files']
            pending_str = f"📄 {pending} pending" if pending > 0 else "✓ No pending"
            
            last_import = info['last_import'][:10] if info['last_import'] else 'Never'
            
            print(f"{status_icon} {broker.upper():<15} | {pending_str:<15} | Last: {last_import}")
        
        print("=" * 60)


def main():
    """CLI entry point for inbox scanner."""
    import sys
    
    # Default paths (can be overridden via .env)
    inbox_path = os.getenv('INBOX_ROOT_PATH', 'G:/Il mio Drive/WAR_ROOM_DATA/inbox')
    processed_path = os.getenv('PROCESSED_ROOT_PATH', 'G:/Il mio Drive/WAR_ROOM_DATA/processed')
    
    scanner = InboxScanner(inbox_path, processed_path)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'status':
            scanner.print_status()
        
        elif command == 'scan':
            pending = scanner.scan_inbox()
            for broker, files in pending.items():
                print(f"\n{broker.upper()}:")
                for f in files:
                    print(f"  - {f.name}")
        
        elif command == 'import':
            results = scanner.import_all_pending()
            for r in results:
                status = '✅' if r['success'] else '❌'
                print(f"{status} {r['broker']}: {r['message']}")
        
        else:
            print(f"Unknown command: {command}")
            print("Usage: python inbox_scanner.py [status|scan|import]")
    else:
        # Default: show status
        scanner.print_status()


if __name__ == "__main__":
    main()
