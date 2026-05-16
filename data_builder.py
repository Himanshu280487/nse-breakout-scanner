import requests
import zipfile
import pandas as pd
import io
from datetime import datetime

# NSE bhavcopy URL format
BASE_URL = "https://archives.nseindia.com/content/historical/EQUITIES/{year}/{month}/cm{day}{month}{year}bhav.csv.zip"

headers = {
    "User-Agent": "Chrome/5.0",
    "Accept": "*/*",
    "Referer": "https://www.nseindia.com"
}

def download_bhavcopy(date):
    """
    Download NSE bhavcopy for a given date
    """

    day = date.strftime("%d")
    month = date.strftime("%b").upper()
    year = date.strftime("%Y")

    url = BASE_URL.format(year=year, month=month, day=day)

    print(f"Downloading: {url}")

    try:
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code != 200:
            print("No data for:", date)
            return None

        z = zipfile.ZipFile(io.BytesIO(r.content))
        file_name = z.namelist()[0]

        df = pd.read_csv(z.open(file_name))

        return df

    except Exception as e:
        print("Error:", e)
        return None


if __name__ == "__main__":
    today = datetime.today()

    df = download_bhavcopy(today)

    if df is not None:
        print(df.head())
        print("\nRows:", len(df))
