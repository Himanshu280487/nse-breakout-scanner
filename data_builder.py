import requests
import zipfile
import pandas as pd
import io

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# NSE bhavcopy URL format
BASE_URL = (
    "https://archives.nseindia.com/content/historical/"
    "EQUITIES/{year}/{month}/cm{day}{month}{year}bhav.csv.zip"
)


# Request headers
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Referer": "https://www.nseindia.com"
}


def get_latest_trading_day():
    """
    Return latest NSE trading day
    (skips Saturday and Sunday)
    """

    # Use Indian timezone
    today = datetime(2025, 5, 24, tzinfo=ZoneInfo("Asia/Kolkata"))

    # Saturday = 5
    # Sunday = 6
    while today.weekday() >= 5:
        today -= timedelta(days=1)

    return today


def download_bhavcopy(date):
    """
    Download NSE bhavcopy for given date
    """

    day = date.strftime("%d")
    month = date.strftime("%b").upper()
    year = date.strftime("%Y")

    url = BASE_URL.format(
        year=year,
        month=month,
        day=day
    )

    print(f"Using trading day: {date.strftime('%d-%b-%Y')}")
    print(f"Downloading: {url}")

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        if response.status_code != 200:
            print(
                f"No data available for "
                f"{date.strftime('%d-%b-%Y')}"
            )
            return None

        # Open zip file from memory
        zip_data = zipfile.ZipFile(
            io.BytesIO(response.content)
        )

        # Get CSV filename
        csv_file = zip_data.namelist()[0]

        # Read CSV into dataframe
        df = pd.read_csv(
            zip_data.open(csv_file)
        )

        return df

    except Exception as e:
        print("Error:", e)
        return None


if __name__ == "__main__":
    print("Current IST Time:", datetime.now(ZoneInfo("Asia/Kolkata")))
    latest_day = get_latest_trading_day()

    df = download_bhavcopy(latest_day)

    if df is not None:
        print("\nBhavcopy Loaded Successfully")
        print(df.head())
        print("\nTotal Rows:", len(df))
