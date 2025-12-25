from services.market_data_service import get_asset_details
import sys

ticker = "US26740W1099"
print(f"Testing details for: {ticker}")
details = get_asset_details(ticker)
print(details)

ticker2 = "NVDA"
print(f"Testing details for: {ticker2}")
details2 = get_asset_details(ticker2)
print(details2)
