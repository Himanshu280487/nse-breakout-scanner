import requests
import zipfile
import pandas as pd
import io
from datetime import datetime, timedelta

# NSE bhavcopy URL format
BASE_URL = "https://archives.nseindia.com/content/historical/EQUITIES/{year}/{month}/cm{day}{month}{year}bhav.csv.zip"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Referer": "https://www.nseindia.com"
}


def get_latest_trading_day():
    """
    Return latest trading day (skip weekends)
    """

    today = datetime.today()

    # Saturday = 5, Sunday = 6
    while today.weekday() >= 5:
        today -= timedelta(days=1)

    return today


def download_bhavcopy(date):
    """
    Download NSE bhavcopy for a given date
    """

    day = date.strftime("%d")
    month = date.strftime("%b").upper()
    year = date.strftime("%Y")

    url = BASE_URL.format(
        year=year,
        month=month,
        day=day
    )

    print(f"Downloading: {url}")

    try:
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code != 200:
            print(f"No data available for {date.strftime('%d-%b-%Y')}")
            return None

        z = zipfile.ZipFile(io.BytesIO(r.content))

        file_name = z.namelist()[0]

        df = pd.read_csv(z.open(file_name))

        return df

    except Exception as e:
        print("Error:", e)
        return None


if __name__ == "__main__":

    latest_day = get_latest_trading_day()

    print("Using trading day:", latest_day.strftime("%d-%b-%Y"))

    df = download_bhavcopy(latest_day)

    if df is not None:
        print(df.head())
        print("\nRows:", len(df))
