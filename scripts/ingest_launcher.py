import os
import sys
import importlib
from pathlib import Path
import logging

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
INBOX_DIR = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox")
SCRIPTS_DIR = BASE_DIR / "scripts"

sys.path.append(str(SCRIPTS_DIR))
sys.path.append(str(SCRIPTS_DIR / "brokers"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 INGESTION LAUNCHER STARTED")
    
    if not INBOX_DIR.exists():
        logger.error(f"Inbox not found: {INBOX_DIR}")
        return

    # 1. Scan Inbox for Broker Folders
    broker_folders = [f for f in INBOX_DIR.iterdir() if f.is_dir()]
    
    logger.info(f"Found {len(broker_folders)} broker folders: {[f.name for f in broker_folders]}")
    
    for folder in broker_folders:
        broker_name = folder.name.lower()
        
        # Check if we have a script for this broker
        module_name = f"brokers.{broker_name}"
        
        try:
            # Dynamic Import
            if (SCRIPTS_DIR / "brokers" / f"{broker_name}.py").exists():
                logger.info(f"\n⚡ DETECTED MODULE FOR: {broker_name.upper()}")
                
                module = importlib.import_module(module_name)
                
                # Gather files
                files = [f for f in folder.glob("*") if f.is_file() and not f.name.startswith("~$")]
                if not files:
                    logger.info("   No files in inbox. Skipping.")
                    continue
                
                # EXECUTE EXTRACTION
                logger.info(f"   Launch extraction on {len(files)} files...")
                module.run(files)
                
                # EXECUTE RECONCILIATION
                logger.info("   Running Reconciliation...")
                from reconciliation_engine import reconcile_broker
                reconcile_broker(broker_name)
                
            else:
                logger.warning(f"⚠️ No extraction script found for '{broker_name}'. Skipping.")
                
        except Exception as e:
            logger.error(f"❌ Error processing {broker_name}: {e}")

    logger.info("\n✅ INGESTION COMPLETE.")

if __name__ == "__main__":
    main()
