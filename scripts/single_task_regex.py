"""
Single-Task Prompt - Ask Qwen for ONE regex at a time

Instead of asking for complete parser, ask for individual regexes.
Then we assemble them ourselves.
"""
import requests
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:14b-instruct-q6_K"

# Sample lines from the PDF
SAMPLES = {
    "trade_buy": "Contrattazione AlphabetInc.ClassA Acquista2@301,93 Pending -",
    "trade_sell": "Contrattazione CanopyGrowthCorp. Vendi-145@2,90CAD 256,83 -",
    "deposit": "Trasferimentodiliquidità Deposito 2.000,00 -",
    "date": "28-nov-2024",
    "isin": "Tassodiconversione IDcontrattazione ISIN\n0,134218 6513054071 DK0062498333"
}

def ask_qwen(question):
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": question,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 500}
        },
        timeout=60
    )
    return response.json().get("response", "")

print("🔍 Asking Qwen for individual regex patterns...")
print("=" * 60)

# 1. BUY trade regex
print("\n1️⃣ BUY TRADE REGEX")
prompt1 = f'''Sample text: "{SAMPLES['trade_buy']}"

Write a Python regex that extracts:
- asset_name (AlphabetInc.ClassA)
- quantity (2)
- price (301,93)

Return ONLY the regex pattern, nothing else.'''

result1 = ask_qwen(prompt1)
print(f"Response: {result1[:200]}")

# 2. SELL trade regex
print("\n2️⃣ SELL TRADE REGEX")
prompt2 = f'''Sample text: "{SAMPLES['trade_sell']}"

Write a Python regex that extracts:
- asset_name (CanopyGrowthCorp.) 
- quantity (145)
- price (2,90)
- currency (CAD)

Return ONLY the regex pattern, nothing else.'''

result2 = ask_qwen(prompt2)
print(f"Response: {result2[:200]}")

# 3. DEPOSIT regex
print("\n3️⃣ DEPOSIT REGEX")
prompt3 = f'''Sample text: "{SAMPLES['deposit']}"

Write a Python regex that extracts:
- amount (2.000,00)

Return ONLY the regex pattern, nothing else.'''

result3 = ask_qwen(prompt3)
print(f"Response: {result3[:200]}")

# 4. DATE regex
print("\n4️⃣ DATE REGEX")
prompt4 = f'''Sample text: "{SAMPLES['date']}"

Write a Python regex to match Italian date format DD-mmm-YYYY.
Examples: 28-nov-2024, 19-dic-2025

Return ONLY the regex pattern, nothing else.'''

result4 = ask_qwen(prompt4)
print(f"Response: {result4[:200]}")

# 5. ISIN regex
print("\n5️⃣ ISIN REGEX")
prompt5 = f'''Sample text: "{SAMPLES['isin']}"

Write a Python regex to extract ISIN code.
ISIN format: 2 uppercase letters + 10 alphanumeric characters.
Example: DK0062498333, US1234567890

Return ONLY the regex pattern, nothing else.'''

result5 = ask_qwen(prompt5)
print(f"Response: {result5[:200]}")

print("\n" + "=" * 60)
print("DONE! Now we can assemble these regexes into a parser.")
