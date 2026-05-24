import requests
import zipfile
import pandas as pd
import io

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# =====================================
# NSE BHAVCOPY URL
# =====================================

BASE_URL = (
    "https://archives.nseindia.com/content/"
    "historical/EQUITIES/{year}/{month}/"
    "cm{day}{month}{year}bhav.csv.zip"
)


# =====================================
# REQUEST HEADERS
# =====================================

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Referer": "https://www.nseindia.com"
}


# =====================================
# GET LATEST TRADING DAY
# =====================================

def get_latest_trading_day():
    """
    Returns latest trading day
    using Indian timezone
    """

    today = datetime.now(
        ZoneInfo("Asia/Kolkata")
    )

    # Skip weekends
    while today.weekday() >= 5:
        today -= timedelta(days=1)

    return today


# =====================================
# DOWNLOAD BHAVCOPY
# =====================================

def download_bhavcopy(date):

    day = date.strftime("%d")
    month = date.strftime("%b").upper()
    year = date.strftime("%Y")

    url = BASE_URL.format(
        year=year,
        month=month,
        day=day
    )

    print(
        f"\nTrying: "
        f"{date.strftime('%d-%b-%Y')}"
    )

    print("Downloading:", url)

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        if response.status_code != 200:
            print("No data found")
            return None

        zip_file = zipfile.ZipFile(
            io.BytesIO(response.content)
        )

        csv_name = zip_file.namelist()[0]

        df = pd.read_csv(
            zip_file.open(csv_name)
        )

        return df

    except Exception as e:
        print("Error:", e)
        return None


# =====================================
# FIND AVAILABLE BHAVCOPY
# =====================================

def find_available_bhavcopy():

    date = get_latest_trading_day()

    # Try previous 7 trading days
    for _ in range(7):

        df = download_bhavcopy(date)

        if df is not None:
            print(
                f"\nSUCCESS: "
                f"{date.strftime('%d-%b-%Y')}"
            )
            return df

        # Move back 1 day
        date -= timedelta(days=1)

        # Skip weekends
        while date.weekday() >= 5:
            date -= timedelta(days=1)

    return None


# =====================================
# MAIN
# =====================================

if __name__ == "__main__":

    print(
        "Current IST Time:",
        datetime.now(
            ZoneInfo("Asia/Kolkata")
        )
    )

    df = find_available_bhavcopy()

    if df is not None:

        print("\nBhavcopy Loaded Successfully")

        print(df.head())

        print("\nTotal Rows:", len(df))

    else:

        print(
            "\nERROR: Could not download "
            "any recent bhavcopy"
        )
