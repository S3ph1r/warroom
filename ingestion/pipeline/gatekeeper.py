"""
IDP Pipeline - Module A: Gatekeeper
File validation and filtering with deterministic logic (no AI).
"""
import os
from pathlib import Path
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Allowed extensions (from IDP document)
ALLOWED_EXTENSIONS = {'.csv', '.pdf', '.xls', '.xlsx'}

# File patterns to skip
SKIP_PATTERNS = ['~$', '.DS_Store', 'Thumbs.db', 'desktop.ini']

# MIME types whitelist
ALLOWED_MIMETYPES = {
    'application/pdf',
    'text/csv',
    'text/plain',  # CSV often detected as text/plain
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/octet-stream',  # Some PDFs
}


def is_skippable(filename: str) -> bool:
    """Check if file should be skipped based on name patterns."""
    for pattern in SKIP_PATTERNS:
        if pattern in filename:
            return True
    return False


def validate_extension(file_path: Path) -> Tuple[bool, str]:
    """Validate file extension against whitelist."""
    ext = file_path.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"unsupported_extension:{ext}"
    return True, "ok"


def validate_mime_type(file_path: Path) -> Tuple[bool, str]:
    """
    Validate MIME type using python-magic if available.
    Falls back to extension-based detection if magic not installed.
    """
    try:
        import magic
        mime = magic.from_file(str(file_path), mime=True)
        
        if mime not in ALLOWED_MIMETYPES:
            return False, f"invalid_mime:{mime}"
        return True, "ok"
        
    except ImportError:
        # Fallback: trust extension if magic not available
        logger.warning("python-magic not installed, skipping MIME validation")
        return True, "ok_no_magic"
    except Exception as e:
        logger.error(f"MIME detection failed: {e}")
        return True, "ok_error"


def validate_file(file_path: Path) -> Tuple[bool, str]:
    """
    Complete file validation following IDP Gatekeeper spec.
    
    Returns:
        (is_valid, reason) - reason is "ok" if valid, else error description
    """
    # Check if path exists
    if not file_path.exists():
        return False, "file_not_found"
    
    # Check if it's a file (not directory)
    if not file_path.is_file():
        return False, "not_a_file"
    
    # Skip system/temp files
    if is_skippable(file_path.name):
        return False, "skipped_pattern"
    
    # Validate extension
    valid, reason = validate_extension(file_path)
    if not valid:
        return False, reason
    
    # Validate MIME type
    valid, reason = validate_mime_type(file_path)
    if not valid:
        return False, reason
    
    return True, "ok"


def get_broker_from_path(file_path: Path) -> Optional[str]:
    """
    Extract broker name from path structure.
    Expected: /inbox/{broker_name}/{filename}
    """
    parts = file_path.parts
    
    # Find "inbox" in path and get next part
    for i, part in enumerate(parts):
        if part.lower() == 'inbox' and i + 1 < len(parts):
            return parts[i + 1].upper().replace(' ', '_')
    
    # Fallback: use parent directory name
    return file_path.parent.name.upper().replace(' ', '_')


class Gatekeeper:
    """
    The Gatekeeper class - validates and filters incoming files.
    """
    
    def __init__(self, discard_folder: Optional[Path] = None):
        self.discard_folder = discard_folder
        self.stats = {
            'processed': 0,
            'accepted': 0,
            'rejected': 0,
            'rejections_by_reason': {}
        }
    
    def process_file(self, file_path: Path) -> Tuple[bool, str, Optional[str]]:
        """
        Process a single file through the gatekeeper.
        
        Returns:
            (accepted, reason, broker_name)
        """
        self.stats['processed'] += 1
        
        valid, reason = validate_file(file_path)
        
        if valid:
            self.stats['accepted'] += 1
            broker = get_broker_from_path(file_path)
            logger.info(f"✅ ACCEPTED: {file_path.name} -> Broker: {broker}")
            return True, reason, broker
        else:
            self.stats['rejected'] += 1
            self.stats['rejections_by_reason'][reason] = \
                self.stats['rejections_by_reason'].get(reason, 0) + 1
            
            logger.warning(f"❌ REJECTED: {file_path.name} -> {reason}")
            
            # Move to discard folder if configured
            if self.discard_folder:
                self._move_to_discard(file_path, reason)
            
            return False, reason, None
    
    def _move_to_discard(self, file_path: Path, reason: str):
        """Move rejected file to discard folder."""
        import shutil
        
        reason_folder = self.discard_folder / reason.split(':')[0]
        reason_folder.mkdir(parents=True, exist_ok=True)
        
        dest = reason_folder / file_path.name
        try:
            shutil.move(str(file_path), str(dest))
            logger.info(f"   Moved to: {dest}")
        except Exception as e:
            logger.error(f"   Failed to move: {e}")
    
    def get_stats(self) -> dict:
        """Return processing statistics."""
        return self.stats.copy()
