from googleapiclient.discovery import build
from google.oauth2 import service_account

SERVICE_ACCOUNT_FILE = "workout-dashboard-476518-f4b943386f4f.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SHEET_ID = "1hwTeWjYiuWh6yjjpomGZ5WaxOaAngfuQn8uMdZPyjOk"
RANGE = "2025!A:F"

def main():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=creds)
    resp = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=RANGE
    ).execute()
    values = resp.get("values", [])
    if not values:
        print("No data found.")
        return
    headers = values[0]
    rows = values[1:]
    print(f"Headers: {headers}")
    print("First 10 rows:")
    for r in rows[:10]:
        print(r)
    print(f"Total rows (excluding header): {len(rows)}")

if __name__ == "__main__":
    main()
