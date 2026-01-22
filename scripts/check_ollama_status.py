
import sys
import os
import requests
import colorama
from colorama import Fore, Style

colorama.init()

def check_ollama():
    print(f"\n{Fore.CYAN}[*] Verifying AI Engine (Ollama) Connectivity...{Style.RESET_ALL}")
    
    # Check Environment
    host = os.getenv("OLLAMA_HOST", "localhost")
    port = "11434"
    url = f"http://{host}:{port}/api/tags"
    
    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            print(f"{Fore.GREEN}[+] SUCCESS: Ollama is reachable at {url}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}[!] ERROR: Ollama returned status code {response.status_code}{Style.RESET_ALL}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"{Fore.RED}[!] FAILURE: Could not connect to {url}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}    HINT: If running in WSL, ensure it binds to valid IP:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}    1. Open WSL terminal{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}    2. Run: export OLLAMA_HOST=0.0.0.0{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}    3. Run: ollama serve{Style.RESET_ALL}")
        return False
        
if __name__ == "__main__":
    success = check_ollama()
    sys.exit(0 if success else 1)
