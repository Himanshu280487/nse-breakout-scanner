import pandas as pd
import requests
import io


def get_nse_stocks():

    url = (
        "https://nsearchives.nseindia.com/"
        "content/equities/EQUITY_L.csv"
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept": "text/csv,*/*",
        "Referer": "https://www.nseindia.com/"
    }

    try:

        session = requests.Session()

        # Visit NSE homepage first
        session.get(
            "https://www.nseindia.com",
            headers=headers,
            timeout=20
        )

        # Download CSV
        response = session.get(
            url,
            headers=headers,
            timeout=20
        )

        response.raise_for_status()

        # Read CSV
        df = pd.read_csv(
            io.StringIO(response.text)
        )

        # Keep only EQ series
        df = df[df[" SERIES"] == "EQ"]

        # Create Yahoo-compatible symbols
        stocks = (
            df["SYMBOL"]
            .dropna()
            .astype(str)
            .str.strip()
            + ".NS"
        ).tolist()

        return sorted(list(set(stocks)))

    except Exception as e:

        print("ERROR:", e)

        return []


# =========================
# TEST
# =========================

if __name__ == "__main__":

    stocks = get_nse_stocks()

    print(
        f"\nTotal NSE Stocks: {len(stocks)}"
    )

    print("\nFirst 20 Stocks:\n")

    print(stocks[:20])
