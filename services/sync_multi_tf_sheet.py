from datetime import datetime, timezone
from services.twelve_data_multi_tf import fetch_multi_tf_high_low
from services.google_sheets_service import PrivateGoogleSheetsService

def sync_multi_timeframe_data():
    print("Fetching multi-timeframe data from Twelve Data...")
    data = fetch_multi_tf_high_low()
    
    ws = PrivateGoogleSheetsService()._worksheet("TF_Master")
    headers = ws.row_values(1)
    
    if not headers or "Timeframe" not in headers:
        print("Headers not found! Creating default headers...")
        headers = ["Timeframe", "Date", "High", "Low", "Buy Base", "Sell Base", "Last Updated"]
        ws.append_row(headers)
        
    tf_col_idx = headers.index("Timeframe") + 1
    tf_values = ws.col_values(tf_col_idx)
    
    for item in data:
        tf = item["Timeframe"]
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        if tf in tf_values:
            # Overwrite existing timeframe row
            row_idx = tf_values.index(tf) + 1
            ws.update_cell(row_idx, headers.index("Date") + 1, item["Date"])
            ws.update_cell(row_idx, headers.index("High") + 1, item["High"])
            ws.update_cell(row_idx, headers.index("Low") + 1, item["Low"])
            ws.update_cell(row_idx, headers.index("Last Updated") + 1, now_utc)
            print(f"✅ Updated existing {tf} row.")
        else:
            # Create new timeframe row
            row_data = [
                tf, item["Date"], item["High"], item["Low"], 
                "", "", now_utc
            ]
            ws.append_row(row_data)
            print(f"✅ Appended new {tf} row.")
            
    print("🚀 Google Sheet Multi-Timeframe sync complete!")

if __name__ == "__main__":
    sync_multi_timeframe_data()
