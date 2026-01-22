"""
IDP Pipeline - Main Entry Point
Orchestrates the complete ingestion workflow.
"""
import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.pipeline.gatekeeper import Gatekeeper
from ingestion.pipeline.router import DocumentRouter, DocumentType
from ingestion.pipeline.extraction_engine import ExtractionEngine
from ingestion.pipeline.data_loader import DataLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Default paths
DEFAULT_INBOX = Path(os.getenv("INBOX_PATH", "G:/Il mio Drive/WAR_ROOM_DATA/inbox"))
DEFAULT_PROCESSED = Path(os.getenv("PROCESSED_PATH", "G:/Il mio Drive/WAR_ROOM_DATA/processed"))
DEFAULT_DISCARDED = Path(os.getenv("DISCARDED_PATH", "G:/Il mio Drive/WAR_ROOM_DATA/discarded"))


class IDPPipeline:
    """
    Main IDP Pipeline orchestrator.
    Combines all 4 modules into a cohesive workflow.
    """
    
    def __init__(
        self,
        inbox_path: Path = DEFAULT_INBOX,
        processed_path: Path = DEFAULT_PROCESSED,
        discarded_path: Path = DEFAULT_DISCARDED,
        dry_run: bool = False
    ):
        self.inbox_path = inbox_path
        self.processed_path = processed_path
        self.discarded_path = discarded_path
        self.dry_run = dry_run
        
        # Initialize modules
        self.gatekeeper = Gatekeeper(discard_folder=discarded_path if not dry_run else None)
        self.router = DocumentRouter()
        self.extraction_engine = ExtractionEngine()
        self.data_loader = DataLoader()
        
        self.results = {
            'processed': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
    
    def process_file(self, file_path: Path) -> dict:
        """
        Process a single file through the complete pipeline.
        
        Returns:
            Result dict with status and details
        """
        result = {
            'file': file_path.name,
            'status': 'pending',
            'broker': None,
            'doc_type': None,
            'records': 0,
            'error': None
        }
        
        try:
            # Module A: Gatekeeper
            valid, reason, broker = self.gatekeeper.process_file(file_path)
            
            if not valid:
                result['status'] = 'rejected'
                result['error'] = reason
                self.results['skipped'] += 1
                return result
            
            result['broker'] = broker
            
            # Module B: Router (Classification)
            classification = self.router.classify(file_path)
            
            if classification.category == DocumentType.TRASH:
                result['status'] = 'trash'
                result['error'] = classification.reasoning
                self.results['skipped'] += 1
                return result
            
            if not classification.is_valid():
                result['status'] = 'low_confidence'
                result['error'] = f"Confidence {classification.confidence:.2f} below threshold"
                self.results['skipped'] += 1
                return result
            
            result['doc_type'] = classification.category.value
            
            # Module C: Extraction Engine
            logger.info(f"📥 Extracting data from {file_path.name}...")
            data = self.extraction_engine.extract(file_path, broker, classification.category)
            
            if not data:
                result['status'] = 'extraction_failed'
                result['error'] = 'No data extracted'
                self.results['failed'] += 1
                return result
            
            result['records'] = len(data)
            
            # Module D: Data Loader (skip in dry run)
            if not self.dry_run:
                if classification.category == DocumentType.HOLDINGS:
                    count = self.data_loader.load_holdings(broker, data, file_path.name)
                else:
                    count = self.data_loader.load_transactions(broker, data, file_path.name)
                
                # Log import
                self.data_loader.log_import(
                    broker=broker,
                    filename=file_path.name,
                    file_path=str(file_path),
                    holdings_count=count if classification.category == DocumentType.HOLDINGS else 0,
                    transactions_count=count if classification.category == DocumentType.TRANSACTIONS else 0,
                )
                
                # Move to processed
                self._move_to_processed(file_path, broker)
            
            result['status'] = 'success'
            self.results['success'] += 1
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            self.results['failed'] += 1
            logger.exception(f"Error processing {file_path.name}")
        
        self.results['processed'] += 1
        self.results['details'].append(result)
        
        return result
    
    def process_broker(self, broker: str) -> list:
        """
        Process all files for a specific broker.
        
        Args:
            broker: Broker folder name (e.g., "bgsaxo")
        
        Returns:
            List of processing results
        """
        broker_folder = self.inbox_path / broker.lower()
        
        if not broker_folder.exists():
            logger.error(f"Broker folder not found: {broker_folder}")
            return []
        
        files = list(broker_folder.glob("*"))
        logger.info(f"\n{'='*60}")
        logger.info(f"🏦 Processing broker: {broker.upper()}")
        logger.info(f"   Found {len(files)} files in inbox")
        logger.info(f"{'='*60}\n")
        
        results = []
        for file_path in files:
            if file_path.is_file():
                logger.info(f"\n📄 File: {file_path.name}")
                result = self.process_file(file_path)
                results.append(result)
                self._print_result(result)
        
        return results
    
    def process_all(self) -> dict:
        """
        Process all files from all brokers in inbox.
        
        Returns:
            Summary of all processing
        """
        logger.info(f"\n{'='*60}")
        logger.info("🚀 IDP PIPELINE - FULL RUN")
        logger.info(f"   Inbox: {self.inbox_path}")
        logger.info(f"   Dry Run: {self.dry_run}")
        logger.info(f"{'='*60}\n")
        
        if not self.inbox_path.exists():
            logger.error(f"Inbox path not found: {self.inbox_path}")
            return self.results
        
        # Find all broker folders
        brokers = [d for d in self.inbox_path.iterdir() if d.is_dir()]
        
        for broker_folder in brokers:
            self.process_broker(broker_folder.name)
        
        self._print_summary()
        return self.results
    
    def _move_to_processed(self, file_path: Path, broker: str):
        """Move file to processed folder."""
        import shutil
        
        dest_folder = self.processed_path / broker.lower()
        dest_folder.mkdir(parents=True, exist_ok=True)
        
        # Add timestamp to avoid overwrites
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_name = f"{timestamp}_{file_path.name}"
        dest_path = dest_folder / dest_name
        
        try:
            shutil.move(str(file_path), str(dest_path))
            logger.info(f"   📁 Moved to: {dest_path}")
        except Exception as e:
            logger.error(f"   Failed to move file: {e}")
    
    def _print_result(self, result: dict):
        """Print single file result."""
        status_icons = {
            'success': '✅',
            'rejected': '⛔',
            'trash': '🗑️',
            'low_confidence': '⚠️',
            'extraction_failed': '❌',
            'error': '💥'
        }
        
        icon = status_icons.get(result['status'], '❓')
        msg = f"   {icon} Status: {result['status']}"
        
        if result['records']:
            msg += f" | Records: {result['records']}"
        if result['error']:
            msg += f" | Error: {result['error']}"
        
        logger.info(msg)
    
    def _print_summary(self):
        """Print processing summary."""
        logger.info(f"\n{'='*60}")
        logger.info("📊 PROCESSING SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"   Total processed: {self.results['processed']}")
        logger.info(f"   ✅ Successful: {self.results['success']}")
        logger.info(f"   ❌ Failed: {self.results['failed']}")
        logger.info(f"   ⏭️ Skipped: {self.results['skipped']}")
        
        # Module stats
        logger.info(f"\n📈 Module Statistics:")
        logger.info(f"   Gatekeeper: {self.gatekeeper.get_stats()}")
        logger.info(f"   Router: {self.router.get_stats()}")
        logger.info(f"   Extraction: {self.extraction_engine.get_stats()}")
        logger.info(f"   Loader: {self.data_loader.get_stats()}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="IDP Pipeline - Financial Document Ingestion"
    )
    
    parser.add_argument(
        '--broker', '-b',
        type=str,
        help='Process specific broker (e.g., bgsaxo, binance)'
    )
    
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Dry run: extract data but do not load to DB or move files'
    )
    
    parser.add_argument(
        '--inbox', '-i',
        type=str,
        default=str(DEFAULT_INBOX),
        help='Path to inbox folder'
    )
    
    parser.add_argument(
        '--file', '-f',
        type=str,
        help='Process single file (provide full path)'
    )
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = IDPPipeline(
        inbox_path=Path(args.inbox),
        dry_run=args.dry_run
    )
    
    # Run
    if args.file:
        # Single file mode
        result = pipeline.process_file(Path(args.file))
        pipeline._print_result(result)
    elif args.broker:
        # Single broker mode
        pipeline.process_broker(args.broker)
    else:
        # Full run
        pipeline.process_all()


if __name__ == "__main__":
    main()
