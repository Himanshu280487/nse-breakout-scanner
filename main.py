import yfinance as yf
import numpy as np
import smtplib
import os

from email.mime.text import MIMEText
from datetime import datetime

# =========================
# SETTINGS
# =========================

MIN_AGE_YEARS = 3
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
    stocks = [x.strip() for x in f.readlines() if x.strip()]

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

        if df is None or df.empty or len(df) < 50:
            continue

        # =========================
        # CLEAN DATA
        # =========================

        df = df.dropna()

        close = df["Close"].values
        high = df["High"].values
        volume = df["Volume"].values
        dates = df.index

        current_close = float(close[-1])
        current_volume = float(volume[-1])
        current_date = dates[-1]

        if current_close < MIN_PRICE:
            continue

        # =========================
        # TRUE ATH LOGIC
        # =========================

        ath_index = np.argmax(high)
        ath_price = float(high[ath_index])
        ath_date = dates[ath_index]

        years_since_ath = (current_date - ath_date).days / 365.25

        # must be REAL old base
        if years_since_ath < MIN_AGE_YEARS:
            continue

        breakout = current_close > ath_price

        # =========================
        # VOLUME LOGIC
        # =========================

        hist_volume = volume[:-1]
        avg_volume = np.mean(hist_volume[-VOLUME_LOOKBACK:])

        if avg_volume == 0:
            continue

        volume_ratio = current_volume / avg_volume

        high_volume = volume_ratio >= MIN_VOLUME_RATIO

        # =========================
        # FINAL CHECK
        # =========================

        if breakout and high_volume:

            results.append(
                f"""
STOCK: {stock}

ATH Price: {ath_price:.2f}
ATH Age: {years_since_ath:.1f} years

Breakout Price: {current_close:.2f}
Volume Spike: {volume_ratio:.2f}x
                """
            )

    except Exception as e:
        print(f"ERROR in {stock}: {e}")

# =========================
# EMAIL
# =========================

body = "\n\n----------------\n\n".join(results) if results else "No valid breakouts found."

msg = MIMEText(body)
msg["Subject"] = f"NSE Multi-Year Breakout Scanner - {datetime.now().date()}"
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
