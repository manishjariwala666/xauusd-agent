import os
import json
from urllib.request import Request, urlopen
from urllib.parse import urlencode

TWELVE_DATA_URL = "https://api.twelvedata.com/time_series"

def fetch_multi_tf_high_low() -> list:
    """Fetch Daily, Weekly, and Monthly High/Low from Twelve Data."""
    api_key = os.getenv("TWELVE_DATA_API_KEY", "").strip()
    
    # Naya logic: Agar key nahi mili toh terminal par maangega
    if not api_key:
        api_key = input("\n🔑 Apni Twelve Data API Key yahan paste kariye aur Enter dabaiye: ").strip()
        if not api_key:
            raise RuntimeError("API Key blank chhod di gayi hai.")

    timeframes = {"1day": "Daily", "1week": "Weekly", "1month": "Monthly"}
    results = []

    for tf_code, tf_name in timeframes.items():
        query = urlencode({
            "symbol": "XAU/USD",
            "interval": tf_code,
            "outputsize": 2, 
            "timezone": "UTC"
        })
        
        request = Request(
            f"{TWELVE_DATA_URL}?{query}",
            headers={"Authorization": f"apikey {api_key}"}
        )
        
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
                
                values = payload.get("values")
                if values and len(values) > 1:
                    prev_candle = values[1] 
                    results.append({
                        "Timeframe": tf_name,
                        "Date": prev_candle["datetime"],
                        "High": float(prev_candle["high"]),
                        "Low": float(prev_candle["low"])
                    })
        except Exception as e:
            print(f"Failed to fetch {tf_name} data: {e}")
            
    return results
