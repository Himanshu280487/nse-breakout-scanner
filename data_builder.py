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
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/"
}


# =====================================
# GET LATEST TRADING DAY
# =====================================

def get_latest_trading_day():
    """
    Return latest NSE trading day
    """

    # TEMP FIX FOR WRONG SERVER CLOCK
    today = datetime(
        2025,
        5,
        24,
        tzinfo=ZoneInfo("Asia/Kolkata")
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

        session = requests.Session()

        # Visit NSE homepage first
        session.get(
            "https://www.nseindia.com",
            headers=HEADERS,
            timeout=20
        )

        # Small delay
        import time
        time.sleep(2)

        # Download bhavcopy
        response = session.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        if response.status_code != 200:

            print(
                "HTTP Error:",
                response.status_code
            )

            return None

        # NSE sometimes returns HTML block page
        if b"<!DOCTYPE html>" in response.content[:200]:

            print("NSE blocked request")

            return None

        # Read ZIP file
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

        # Go back 1 day
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
