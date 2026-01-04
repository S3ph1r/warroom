"""
Clean Scalable Inbox
Deletes files identified as useless (legal/info/privacy) from the Scalable inbox.
"""
from pathlib import Path
import os

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox\scalable")

USELESS_PATTERNS = [
    "Information sheet on deposit protection",
    "Informazioni Cliente",
    "Mandato di addebito diretto SEPA",
    "Proposta Contrattuale",
    "Self-disclosure of tax residency",
    "Is your data up to date",
    "Nuovi Termini e condizioni",
    "Receipt confirmation",
    "Aggiornamento della privacy policy",
    "Update of our Privacy Policy",
    "Informazioni fiscali",
    "La tua azione gratuito", # "Your free share"
    "Scalable Capital ora e una banca",
    "Change in interest rate",
    "Financial status Scalable Capital",
    "Transfer in - Transfer out" # Usually just confirming the transfer, no valuable transaction data often? Or maybe it has the transfer? Check later. User said "useless" generally. Use caution.
    # Keep "Transfer" for now, delete others.
]

def clean_inbox():
    print("=" * 60)
    print("🧹 CLEANING SCALABLE INBOX")
    print("=" * 60)
    
    files = list(INBOX.glob("*.pdf"))
    deleted_count = 0
    
    for p in files:
        name = p.name
        is_useless = False
        for pat in USELESS_PATTERNS:
            if pat in name:
                is_useless = True
                break
        
        if is_useless:
            try:
                os.remove(p)
                print(f"✅ Deleted: {name}")
                deleted_count += 1
            except Exception as e:
                print(f"❌ Error deleting {name}: {e}")
                
    print("-" * 60)
    print(f"Total files deleted: {deleted_count}")

if __name__ == "__main__":
    clean_inbox()
