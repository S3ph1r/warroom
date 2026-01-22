
import requests
import sys
import os
from colorama import init, Fore, Style

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from scripts.check_ollama_status import check_ollama
except ImportError:
    # Fallback if running from root
    from check_ollama_status import check_ollama

init()

API_URL = "http://127.0.0.1:8000"

def print_status(component, status, message=""):
    color = Fore.GREEN if status else Fore.RED
    symbol = "✅" if status else "❌"
    print(f"{symbol} {component:<20}: {color}{'PASS' if status else 'FAIL'}{Style.RESET_ALL} {message}")

def test_backend():
    print(f"\n{Fore.CYAN}--- BACKEND API CHECKS ---{Style.RESET_ALL}")
    
    # 1. Health
    try:
        r = requests.get(f"{API_URL}/api/status", timeout=2)
        print_status("System Health", r.status_code == 200, f"(Status: {r.status_code})")
    except:
        print_status("System Health", False, "(Connection Refused - Backend down?)")
        return False

    # 2. Portfolio
    try:
        r = requests.get(f"{API_URL}/api/portfolio", timeout=5)
        data = r.json()
        valid = "total_value" in data and "holdings" in data
        print_status("Portfolio Data", r.status_code == 200 and valid, f"(Items: {len(data.get('holdings', []))})")
    except Exception as e:
        print_status("Portfolio Data", False, str(e))

    # 3. Intelligence
    try:
        r = requests.get(f"{API_URL}/api/intelligence", timeout=5)
        data = r.json()
        print_status("Intelligence Data", r.status_code == 200, f"(Items: {len(data)})")
    except Exception as e:
        print_status("Intelligence Data", False, str(e))

    # 4. Council History (New Feature)
    try:
        r = requests.get(f"{API_URL}/api/council/history", timeout=5)
        if r.status_code == 404:
            print_status("Council History", False, f"{Fore.YELLOW}(Endpoint 404 - RESTART REQUIRED to activate new features){Style.RESET_ALL}")
        elif r.status_code == 200:
            data = r.json()
            print_status("Council History", True, f"(Available Dates: {len(data)})")
        else:
             print_status("Council History", False, f"(Status: {r.status_code})")
    except Exception as e:
        print_status("Council History", False, str(e))
        
    return True

def main():
    print(f"\n{Fore.YELLOW}🚀 STARTING FULL SYSTEM VERIFICATION...{Style.RESET_ALL}")
    
    # 1. Check AI
    print(f"\n{Fore.CYAN}--- AI ENGINE CHECK ---{Style.RESET_ALL}")
    ai_status = check_ollama()
    
    # 2. Check Backend
    backend_status = test_backend()
    
    print(f"\n{Fore.YELLOW}--- SUMMARY ---{Style.RESET_ALL}")
    if ai_status and backend_status:
         print(f"{Fore.GREEN}System Verification Complete.{Style.RESET_ALL}")
    else:
         print(f"{Fore.RED}System Verification Found Issues.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
