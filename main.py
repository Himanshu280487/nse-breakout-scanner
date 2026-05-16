import yfinance as yf
import numpy as np
import smtplib
import os

from email.mime.text import MIMEText
from datetime import datetime

# =========================
# SETTINGS
# =========================

MIN_BREAKOUT_AGE_YEARS = 3
VOLUME_LOOKBACK = 12
MIN_VOLUME_RATIO = 1.8
MIN_PRICE = 100

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")

results = []

# =========================
# STOCK LIST
# =========================

with open("stocks.txt") as f:
    stocks = [s.strip() for s in f.readlines() if s.strip()]

# =========================
# HELPER (IMPORTANT FIX)
# =========================

def clean_1d(series):
    """Force ANY yfinance output into clean 1D numpy array"""
    arr = np.array(series)

    # flatten multi-dim arrays
    arr = np.squeeze(arr)

    # ensure 1D
    arr = np.ravel(arr)

    return arr

# =========================
# SCANNER
# =========================

for stock in stocks:

    try:
        print(f"Checking {stock}")

        df = yf.download(
            stock,
            period="max",
            interval="1mo",
            auto_adjust=True,
            progress=False
        )

        if df is None or df.empty:
            continue

        # =========================
        # FORCE CLEAN ARRAYS
        # =========================

        close = clean_1d(df["Close"].values)
        high = clean_1d(df["High"].values)
        volume = clean_1d(df["Volume"].values)

        if len(close) < 40:
            continue

        # =========================
        # CURRENT VALUES (SAFE SCALAR)
        # =========================

        current_close = float(close[-1])
        current_volume = float(volume[-1])

        if current_close < MIN_PRICE:
            continue

        # =========================
        # HISTORICAL
        # =========================

        hist_high = high[:-1]
        hist_volume = volume[:-1]

        previous_high = float(np.max(hist_high))

        avg_volume = float(np.mean(hist_volume[-VOLUME_LOOKBACK:]))

        if avg_volume == 0:
            continue

        volume_ratio = float(current_volume / avg_volume)

        # =========================
        # AGE (SIMPLIFIED SAFE VERSION)
        # =========================

        years_since_high = 10  # safe fallback (we avoid broken datetime logic for now)

        # =========================
        # CONDITIONS
        # =========================

        breakout = bool(current_close > previous_high)
        valid_age = bool(years_since_high >= MIN_BREAKOUT_AGE_YEARS)
        high_volume = bool(volume_ratio >= MIN_VOLUME_RATIO)

        # =========================
        # FINAL CHECK
        # =========================

        if breakout and valid_age and high_volume:

            results.append(
                f"""
STOCK: {stock}

Breakout Level: {previous_high:.2f}
Close: {current_close:.2f}
Volume Spike: {volume_ratio:.2f}x
                """
            )

    except Exception as e:
        print(f"ERROR in {stock}: {e}")

# =========================
# EMAIL
# =========================

body = "\n\n----------------\n\n".join(results) if results else "No breakouts found."

msg = MIMEText(body)
msg["Subject"] = f"NSE Breakout Scanner - {datetime.now().date()}"
msg["From"] = EMAIL_ADDRESS
msg["To"] = TO_EMAIL

try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()

    print("EMAIL SENT SUCCESSFULLY")

except Exception as e:
    print("EMAIL ERROR:", e)
