"""
Smart Orchestrator - Complete Document Processing Pipeline

Combines:
1. Prescan (broker extraction, fingerprinting, deduplication)
2. Two-phase classification (understanding + mapping)
3. Decision logic (process vs skip)
4. Registry updates
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import re

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from scripts.smart_prescan import scan_inbox, mark_processed, mark_skipped, load_registry, save_registry
from scripts.smart_classifier import classify_document


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("warroom_ingestion.log", mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger("SmartOrchestrator")


# Document types that should be SKIPPED (no trading data)
# Removed "CASH_MOVEMENTS" from skip list to allow tracking of Cash Balances (EUR, USD)
SKIP_TYPES = ["ACCOUNT", "UNKNOWN"]


def orchestrate_inbox(inbox_path: Path) -> dict:
    """
    Full orchestration pipeline:
    1. Prescan and fingerprint all files
    2. Classify each file
    3. Decide what to process/skip
    4. Update registry
    """
    inbox = Path(inbox_path)
    
    logger.info("="*60)
    logger.info("🎼 SMART ORCHESTRATOR - Starting Full Pipeline")
    logger.info("="*60)
    
    # Step 1: Prescan
    logger.info("\n📂 PHASE 1: PRESCAN")
    files_to_process = scan_inbox(inbox)
    
    if not files_to_process:
        logger.info("   No new files to process.")
        return {"processed": 0, "skipped": 0, "files": []}
    
    # Step 2: Sort files by type to minimize LLM switching
    # Process all Excel/CSV first (Qwen), then all PDFs (Vision)
    def file_type_priority(f):
        ext = Path(f["filepath"]).suffix.lower()
        if ext in ['.xlsx', '.xls', '.csv']:
            return 0  # Qwen first
        elif ext == '.pdf':
            return 1  # Vision second
        return 2
    
    files_to_process = sorted(files_to_process, key=file_type_priority)
    
    # Step 3: Classify each file
    logger.info(f"\n🧠 PHASE 2: CLASSIFICATION ({len(files_to_process)} files)")
    logger.info("   📋 Order: Excel/CSV first (Qwen), then PDFs (Vision)")
    
    candidates = []
    skipped = []
    errors = []
    
    for file_info in files_to_process:
        filepath = file_info["filepath"]
        broker = file_info["broker"]
        fingerprint = file_info["fingerprint"]
        
        logger.info(f"\n{'='*50}")
        logger.info(f"📄 [{broker}] {filepath.name}")
        
        try:
            classification = classify_document(filepath)
            
            if "error" in classification:
                logger.error(f"   ❌ Classification error: {classification['error']}")
                errors.append({"file": str(filepath), "broker": broker, "error": classification["error"]})
                continue
            
            doc_type = classification.get("document_type", "UNKNOWN")
            should_process = classification.get("should_process", False)
            
            logger.info(f"   📊 Type: {doc_type}")
            logger.info(f"   ✅ Process: {should_process}")
            
            if doc_type in SKIP_TYPES or not should_process:
                reason = classification.get("_phase1_reasoning") or classification.get("skip_reason") or "No trading data detected"
                logger.info(f"   ⏭️ SKIPPING: {reason[:60]}...")
                mark_skipped(filepath, reason)
                skipped.append({
                    "file": str(filepath),
                    "broker": broker,
                    "reason": reason,
                    "document_type": doc_type,
                    "asset_type": classification.get("asset_type", "UNKNOWN"),
                    "classification": classification
                })
            else:
                logger.info(f"   ✅ CANDIDATE for processing")
                candidates.append({
                    "file": str(filepath),
                    "broker": broker,
                    "document_type": doc_type,
                    "asset_type": classification.get("asset_type", "UNKNOWN"),
                    "classification": classification,
                    "fingerprint": fingerprint,
                    "is_pdf": filepath.suffix.lower() == '.pdf'
                })
                
        except Exception as e:
            logger.error(f"   ❌ Exception: {e}")
            errors.append({"file": str(filepath), "broker": broker, "error": str(e)})

    # Step 4: Deduplication (Logic-based)
    logger.info(f"\n🔍 PHASE 3: LOGICAL DEDUPLICATION ({len(candidates)} candidates)")
    
    final_processed = []
    
    # Group by Broker + Year (from filename or content)
    # Simple heuristic: if we have Excel and PDF for same broker/year, drop PDF
    import re
    def extract_year(f):
        match = re.search(r"20\d{2}", Path(f).name)
        return match.group(0) if match else "unknown"

    groups = {}
    for c in candidates:
        year = extract_year(c["file"])
        key = f"{c['broker']}_{year}"
        if key not in groups: groups[key] = []
        groups[key].append(c)
        
    for key, group in groups.items():
        if len(group) > 1:
            # Check if we have mixed formats
            has_excel = any(not x["is_pdf"] for x in group)
            has_pdf = any(x["is_pdf"] for x in group)
            
            if has_excel and has_pdf:
                logger.info(f"   redundancy found in group {key} (Excel+PDF)")
                # Keep Excels, skip PDFs
                for item in group:
                    if item["is_pdf"]:
                        logger.info(f"   🗑️ Dropping redundant PDF: {Path(item['file']).name}")
                        mark_skipped(Path(item["file"]), "Redundant: Excel version exists")
                        skipped.append({"file": item["file"], "broker": item["broker"], "reason": "Redundant: Excel version exists"})
                    else:
                        final_processed.append(item)
            else:
                # No mixed formats, keep all (or implement stricter dup check later)
                final_processed.extend(group)
        else:
            final_processed.extend(group)
            
    # Step 5: Finalize
    for item in final_processed:
        # Mark as processed in registry? Or wait until extraction?
        # For now, mark as processed since we decided to ingest it
        # Actually, traditionally we mark processed AFTER extraction success.
        # But here we just return the list to be processed by next stage.
        pass

    return {
        "processed": final_processed,
        "skipped": skipped,
        "errors": errors
    }


def summarize_results(results: dict) -> str:
    """Generate a human-readable summary of orchestration results."""
    lines = []
    
    lines.append("\n" + "="*60)
    lines.append("📋 ORCHESTRATION SUMMARY")
    lines.append("="*60)
    
    # Processed files
    if results["processed"]:
        lines.append(f"\n✅ FILES TO PROCESS ({len(results['processed'])}):")
        for f in results["processed"]:
            lines.append(f"   [{f['broker']}] {Path(f['file']).name}")
            lines.append(f"      Type: {f['document_type']} | Asset: {f['asset_type']}")
            if f.get('column_mapping'):
                mapped = [k for k, v in f['column_mapping'].items() if v]
                lines.append(f"      Columns: {', '.join(mapped)}")
    
    # Skipped files
    if results["skipped"]:
        lines.append(f"\n⏭️ SKIPPED ({len(results['skipped'])}):")
        for f in results["skipped"]:
            lines.append(f"   [{f['broker']}] {Path(f['file']).name}")
            lines.append(f"      Reason: {f['reason'][:50]}...")
    
    # Errors
    if results["errors"]:
        lines.append(f"\n❌ ERRORS ({len(results['errors'])}):")
        for f in results["errors"]:
            lines.append(f"   [{f['broker']}] {Path(f['file']).name}")
            lines.append(f"      Error: {f['error'][:50]}...")
    
    return "\n".join(lines)


# CLI Interface
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python smart_orchestrator.py <inbox_folder>")
        sys.exit(1)
    
    inbox = Path(sys.argv[1])
    
    if inbox.is_dir():
        results = orchestrate_inbox(inbox)
        print(summarize_results(results))
        
        # Save results to file
        output_file = project_root / "orchestration_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n💾 Results saved to: {output_file}")
    else:
        print(f"Error: {inbox} is not a directory")
        sys.exit(1)
