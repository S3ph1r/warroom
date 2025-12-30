"""
IDP Pipeline - Code Generation Prompts Package
"""
from ingestion.prompts.code_generation import (
    PROMPT_CSV_HOLDINGS,
    PROMPT_CSV_TRANSACTIONS,
    PROMPT_PDF_HOLDINGS,
    PROMPT_PDF_TRANSACTIONS,
    PROMPT_FIX_ERROR,
)

__all__ = [
    'PROMPT_CSV_HOLDINGS',
    'PROMPT_CSV_TRANSACTIONS',
    'PROMPT_PDF_HOLDINGS',
    'PROMPT_PDF_TRANSACTIONS',
    'PROMPT_FIX_ERROR',
]
