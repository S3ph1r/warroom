import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from db.database import SessionLocal
from db.models import Holding

# COMPREHENSIVE MAPPING
CORRECTIONS = {
    # Nomi completi / Mixed Case -> Ticker
    "NVIDIA CORP.": "NVDA",
    "NVIDIA Corp.": "NVDA",
    "NVIDIA Corp": "NVDA",
    "SERVICENOW INC.": "NOW",
    "ServiceNow Inc.": "NOW",
    "UBER TECH. DL-": "UBER",
    "UBER TECHNOLOGIES INC": "UBER",
    "UBER TECH. DL-,00001": "UBER",
    "TESLA INC.": "TSLA",
    "Tesla Inc.": "TSLA",
    "TESLA INC. DL -,001": "TSLA",
    "TESLA INC. DL": "TSLA",
    "MICROSOFT CORP.": "MSFT",
    "Microsoft Corp.": "MSFT",
    "AMAZON.COM INC.": "AMZN",
    "Amazon.com Inc.": "AMZN",
    "AMZN": "AMZN",
    "APPLE INC.": "AAPL",
    "Apple Inc.": "AAPL",
    "META PLATFORMS INC.": "META",
    "META PLATFORMS CLASS A": "META",
    "ALPHABET INC. CLASS A": "GOOGL",
    "Alphabet Inc. Class": "GOOGL",
    "GOOGL": "GOOGL",
    "PAYPAL HOLDINGS INC.": "PYPL",
    "PayPal Holdings Inc.": "PYPL",
    "CHEVRON CORP.": "CVX",
    "Chevron Corp.": "CVX",
    "PDD HOLDINGS INC - A": "PDD",
    "PDD Holdings Inc - A": "PDD",
    "NIO INC. - ADR": "NIO",
    "Nio Inc. - ADR": "NIO",
    "XPENG INC. - ADR": "XPEV",
    "XPeng Inc. - ADR": "XPEV",
    "LI AUTO INC. - ADR": "LI",
    "BYD COMPANY LTD - AD": "BYDDY",
    "BYD CO. LTD ADR/2 YC": "BYDDY",
    "BYD Co., Ltd.": "BYDDY",
    "TENCENT HLDGS HD-": "TCEHY",
    "TENCENT HLDGS HD-,00": "TCEHY",
    "Tencent Holdings (KY": "TCEHY",
    "ALIBABA GROUP HLDG L": "BABA",
    "Alibaba Group Hldg (": "BABA",
    "Alibaba Group Holdin": "BABA",
    "BAIDU INC. O.N.": "BIDU",
    "Baidu.com Inc. - ADR": "BIDU",
    "Baidu A": "BIDU",
    "XIAOMI CORP.": "XIACY",
    "Xiaomi (KYG9830T1067": "XIACY",
    "INTEL CORP.": "INTC",
    "Intel Corp.": "INTC",
    "ADVANCED MICRO DEVIC": "AMD",
    "Advanced Micro Devic": "AMD",
    "BROADCOM INC.": "AVGO",
    "Broadcom Inc.": "AVGO",
    "QUALCOMM INC.": "QCOM",
    "TEXAS INSTRUMENTS IN": "TXN",
    "ASML HOLDING": "ASML",
    "KULR TECHNOLOGY GROU": "KULR",
    "KULR Technology Grou": "KULR",
    "VIKING THERAPEUTICS": "VKTX",
    "Viking Therapeutics ": "VKTX",
    "ORACLE CORP.": "ORCL",
    "Oracle Corp.": "ORCL",
    "PALO ALTO NETWORKS I": "PANW",
    "Palo Alto Networks I": "PANW",
    "FORTINET INC.": "FTNT",
    "CROWDSTRIKE HOLDINGS": "CRWD",
    "ZSCALER INC.": "ZS",
    "CLOUDFLARE INC.": "NET",
    "DATADOG INC.": "DDOG",
    "Datadog Inc.": "DDOG",
    "MONGODB INC.": "MDB",
    "SNOWFLAKE INC.": "SNOW",
    "PALANTIR TECHNOLOGIE": "PLTR",
    "Palantir Technologie": "PLTR",
    "DYNATRACE INC.": "DT",
    "Dynatrace Inc.": "DT",
    "ARISTA NETWORKS INC.": "ANET",
    "Arista Networks Inc.": "ANET",
    "CISCO SYSTEMS INC.": "CSCO",
    "IBM CORP.": "IBM",
    "SALESFORCE INC.": "CRM",
    "Salesforce, Inc.": "CRM",
    "ADOBE INC.": "ADBE",
    "Adobe Inc.": "ADBE",
    "AUTODESK INC.": "ADSK",
    "INTUIT INC.": "INTU",
    "BLOCK INC.": "SQ",
    "Block, Inc.": "SQ",
    "SHOPIFY INC.": "SHOP",
    "Shopify Inc.": "SHOP",
    "MERCADOLIBRE INC.": "MELI",
    "SEABOARD CORP.": "SEB",
    "BOOKING HOLDINGS INC": "BKNG",
    "AIRBNB INC.": "ABNB",
    "DOORDASH INC.": "DASH",
    "ROBLOX CORP.": "RBLX",
    "UNITY SOFTWARE INC.": "U",
    "COINBASE GLOBAL INC.": "COIN",
    "Coinbase Global, Inc": "COIN",
    "ROBINHOOD MARKETS IN": "HOOD",
    "MARATHON DIGITAL HOL": "MARA",
    "RIOT PLATFORMS INC.": "RIOT",
    "CLEANSPARK INC.": "CLSK",
    "HUT 8 MINING CORP.": "HUT",
    "MICROSTRATEGY INC.": "MSTR",
    "MicroStrategy Inc.": "MSTR",
    "GALAXY DIGITAL HOLDI": "BRPHF",
    "CELSIUS HOLDINGS INC": "CELH",
    "MONSTER BEVERAGE COR": "MNST",
    "PEPSICO INC.": "PEP",
    "COCA-COLA CO.": "KO",
    "PROCTER & GAMBLE CO.": "PG",
    "JOHNSON & JOHNSON": "JNJ",
    "PFIZER INC.": "PFE",
    "MERCK & CO. INC.": "MRK",
    "ABBVIE INC.": "ABBV",
    "ELI LILLY & CO.": "LLY",
    "NOVO NORDISK A/S": "NVO",
    "NOVO": "NVO",
    "AMPLIFON": "AMP.MI",
    "Amplifon": "AMP.MI",
    "LEONARDO": "LDO.MI",
    "Leonardo": "LDO.MI",
    "FERRARI NV": "RACE.MI",
    "Ferrari NV": "RACE.MI",
    "WEBUILD": "WBD.MI",
    "EUTELSAT COMMUNICATI": "ETL.PA",
    "Eutelsat Communicati": "ETL.PA",
    "THALES S.A.": "HO.PA",
    "Nokia Oyj": "NOKIA.HE",
    "NOKIA": "NOKIA.HE",
    "ZALANDO SE": "ZAL.DE",
    "CARL ZEISS MEDITEC": "AFX.DE",
    "UNITED STATES ANTIMO": "UAMY",
    "United States Antimo": "UAMY",
    "CDT ENVIRONMENTAL TE": "CDT",
    "CDT Environmental Te": "CDT", # Best guess
    "SOLID POWER INC.": "SLDP",
    "Solid Power Inc.": "SLDP",
    "QUANTUM COMPUTING IN": "QUBT",
    "Quantum Computing In": "QUBT",
    "IONQ INC.": "IONQ",
    "RIGETTI COMPUTING IN": "RGTI",
    "D-WAVE QUANTUM INC.": "QBTS",
    "D-Wave Quantum Inc.": "QBTS",
    "D-WAVE QUANTUM DL-,0": "QBTS",
    "QBTS": "QBTS",
    "JOBY AVIATION INCORP": "JOBY",
    "Joby Aviation Incorp": "JOBY",
    "ARCHER AVIATION INC.": "ACHR",
    "LILIUM N.V.": "LILM",
    "AST SPACEMOBILE INC.": "ASTS",
    "AST SpaceMobile Inc.": "ASTS",
    "ROCKET LAB USA INC.": "RKLB",
    "PLANET LABS PBC": "PL",
    "REALBOTIX CORP.": "RBTX",
    "Realbotix Corp.": "RBTX",
    "RBTX": "RBTX",
    "SUBSTRATE ARTIFICIAL": "SAI", 
    "Substrate Artificial": "SAI",
    
    # CRYPTO MAPS (Strip -USD)
    "BTC-USD": "BTC",
    "ETH-USD": "ETH",
    "SOL-USD": "SOL",
    "XRP-USD": "XRP",
    "ADA-USD": "ADA",
    "DOT-USD": "DOT",
    "AVAX-USD": "AVAX",
    "LINK-USD": "LINK",
    "MATIC-USD": "POL",
    "POL-USD": "POL",
    "DOGE-USD": "DOGE",
    "SHIB-USD": "SHIB",
    "TRX-USD": "TRX",
    "LTC-USD": "LTC",
    "BCH-USD": "BCH",
    "XLM-USD": "XLM",
    "USDT": "USDT",
    "USDC": "USDC",
    "USDT-USD": "USDT",
    "USDC-USD": "USDC",
    
    # ETFs
    "ISHARES CORE MSCI WO": "SWDA.MI", 
    "iShares Core MSCI Wo": "SWDA.MI",
    "ISHARES S&P 500": "CSSPX.MI",
    "iShares S&P 500": "CSSPX.MI",
    "ISHARES NASDAQ 100": "CSNDX.MI",
    "VANGUARD S&P 500": "VUSA.AS",
    "VanEck Uranium and N": "NUCL",
}

def fix_tickers():
    print("--- FIXING TICKERS ---")
    session = SessionLocal()
    try:
        holdings = session.query(Holding).all()
        updated = 0
        
        for h in holdings:
            raw = h.ticker
            name = h.name or ""
            
            # Map Ticker
            if raw in CORRECTIONS:
                h.ticker = CORRECTIONS[raw]
                updated += 1
            # Check if Name matches key (if ticker is weird)
            elif name in CORRECTIONS:
                h.ticker = CORRECTIONS[name]
                updated += 1
            # Case insensitive check
            elif raw and raw.upper() in CORRECTIONS:
                 h.ticker = CORRECTIONS[raw.upper()]
                 updated += 1
            
            # Crypto Fix: Strip -USD if present
            if h.asset_type == 'CRYPTO' and h.ticker and h.ticker.endswith('-USD'):
                 h.ticker = h.ticker.replace('-USD', '')
                 updated += 1
                 
        print(f"Updated {updated} holdings.")
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    fix_tickers()
