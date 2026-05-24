import yfinance as yf
import numpy as np
import pandas as pd
import requests
import os
import smtplib
import time
import io

from email.mime.text import MIMEText
from datetime import datetime


# =====================================
# SETTINGS
# =====================================

MIN_PRICE = 100

VOLUME_LOOKBACK = 12
MIN_VOLUME_RATIO = 1.8

BATCH_SIZE = 50


# =====================================
# EMAIL SETTINGS
# =====================================

EMAIL_ADDRESS = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASS")
TO_EMAIL = os.getenv("EMAIL_TO")


# =====================================
# RESULTS
# =====================================

results = []


# =====================================
# NSE STOCK UNIVERSE
# =====================================

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

        # Download stock list CSV
        response = session.get(
            url,
            headers=headers,
            timeout=20
        )

        response.raise_for_status()

        # Read CSV correctly
        df = pd.read_csv(
            io.StringIO(response.text)
        )

        # Keep only EQ stocks
        df = df[
            df[" SERIES"].astype(str).str.strip() == "EQ"
        ]

        # Convert to Yahoo Finance symbols
        stocks = (
            df["SYMBOL"]
            .dropna()
            .astype(str)
            .str.strip()
            + ".NS"
        ).tolist()

        return sorted(list(set(stocks)))

    except Exception as e:

        print("NSE STOCK LOAD ERROR:", e)

        return []


# =====================================
# SAFE SCALAR
# =====================================

def s(x):
    return float(np.asarray(x).squeeze())


# =====================================
# MAIN START
# =====================================

print("\n========================")
print("MAIN.PY STARTED")
print("========================\n")

print("Loading NSE stock universe...")

stocks = get_nse_stocks()

print(f"Stocks loaded: {len(stocks)}")

if len(stocks) == 0:

    print("No stocks loaded - stopping")

    exit()


# =====================================
# SCANNER LOOP
# =====================================

for i in range(0, len(stocks), BATCH_SIZE):

    batch = stocks[i:i + BATCH_SIZE]

    for stock in batch:

        try:

            print("Checking", stock)

            df = yf.download(
                stock,
                period="max",
                interval="1mo",
                auto_adjust=True,
                progress=False
            )

            if (
                df is None
                or df.empty
                or len(df) < 60
            ):
                continue

            close = df["Close"].to_numpy()
            high = df["High"].to_numpy()
            volume = df["Volume"].to_numpy()

            current_close = s(close[-1])
            current_volume = s(volume[-1])

            # Minimum price filter
            if current_close < MIN_PRICE:
                continue

            # =====================================
            # ATH BREAKOUT
            # =====================================

            ath = np.max(high)

            ath_hits = np.where(
                high >= ath * 0.999
            )[0]

            if len(ath_hits) == 0:
                continue

            last_ath_index = ath_hits[-1]

            current_index = len(high) - 1

            consolidation_months = (
                current_index - last_ath_index
            )

            # Minimum 3 years base
            if consolidation_months < 36:
                continue

            breakout = current_close >= ath

            if not breakout:
                continue

            # =====================================
            # VOLUME FILTER
            # =====================================

            avg_volume = s(
                np.mean(
                    volume[-VOLUME_LOOKBACK:-1]
                )
            )

            if avg_volume == 0:
                continue

            volume_ratio = (
                current_volume / avg_volume
            )

            if volume_ratio < MIN_VOLUME_RATIO:
                continue

            # =====================================
            # SCORING
            # =====================================

            breakout_strength = (
                (current_close - ath) / ath
            ) * 100

            breakout_score = min(
                max(breakout_strength * 2, 0),
                30
            )

            volume_score = min(
                volume_ratio * 10,
                40
            )

            base_score = 30

            score = min(
                base_score
                + breakout_score
                + volume_score,
                100
            )

            if score < 60:
                continue

            # =====================================
            # QUALITY LABEL
            # =====================================

            if score >= 80:
                quality = "🔥 STRONG BREAKOUT"

            elif score >= 70:
                quality = "⚡ GOOD BREAKOUT"

            else:
                quality = "⚠️ WEAK BREAKOUT"

            # =====================================
            # SAVE RESULT
            # =====================================

            results.append(f"""

STOCK: {stock}

ATH Breakout: YES
ATH: {ath:.2f}
Close: {current_close:.2f}

Volume Ratio: {volume_ratio:.2f}x
Score: {score:.1f}/100

Quality: {quality}

""")

            # Prevent Yahoo throttling
            time.sleep(1)

        except Exception as e:

            print("Error in", stock, e)


# =====================================
# EMAIL BODY
# =====================================

body = (
    "\n\n------------------------\n\n"
    .join(results)
    if results
    else "No breakouts found."
)

print("\nEMAIL DEBUG")
print("EMAIL_ADDRESS:", EMAIL_ADDRESS)
print(
    "EMAIL_PASSWORD EXISTS:",
    EMAIL_PASSWORD is not None
)
print("TO_EMAIL:", TO_EMAIL)

msg = MIMEText(body)

msg["Subject"] = (
    f"NSE Breakout Scanner - "
    f"{datetime.now().date()}"
)

msg["From"] = EMAIL_ADDRESS
msg["To"] = TO_EMAIL


# =====================================
# SEND EMAIL
# =====================================

try:

    server = smtplib.SMTP(
        "smtp.gmail.com",
        587
    )

    server.starttls()

    server.login(
        EMAIL_ADDRESS,
        EMAIL_PASSWORD
    )

    server.send_message(msg)

    server.quit()

    print("\nEMAIL SENT SUCCESSFULLY")

except Exception as e:

    print("\nEMAIL ERROR:", e)
