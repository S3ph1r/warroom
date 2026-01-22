from pathlib import Path

INBOX = Path(r"G:\Il mio Drive\WAR_ROOM_DATA\inbox")

def count_files():
    print(f"{'BROKER':<20} | {'FILES':<5} | {'SAMPLE'}")
    print("-" * 50)
    
    for broker_dir in sorted(INBOX.iterdir()):
        if not broker_dir.is_dir(): continue
        
        files = list(broker_dir.glob("*"))
        count = len(files)
        sample = files[0].name if files else ""
        
        print(f"{broker_dir.name:<20} | {count:<5} | {sample}")

if __name__ == "__main__":
    count_files()
