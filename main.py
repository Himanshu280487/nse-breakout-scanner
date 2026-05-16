import yfinance as yf
import numpy as np
import os
import smtplib

from email.mime.text import MIMEText
from datetime import datetime

# =========================
# SETTINGS
# =========================

MIN_PRICE = 100
MIN_AGE_YEARS = 3
VOLUME_LOOKBACK = 12
MIN_VOLUME_RATIO = 1.8

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")

results = []

# =========================
# SAFE SCALAR HELPER
# =========================

def s(x):
    """Force any yfinance output into clean float scalar"""
    return float(np.asarray(x).squeeze())

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
        print("Checking", stock)

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
        # DATA CLEAN
        # =========================

        close = df["Close"].to_numpy()
        high = df["High"].to_numpy()
        volume = df["Volume"].to_numpy()
        dates = df.index

        current_close = s(close[-1])
        current_volume = s(volume[-1])

        if current_close < MIN_PRICE:
            continue

        # =========================
        # ATH LOGIC
        # =========================

        hist_high = high[:-1]

        ath_price = s(np.max(hist_high))
        ath_index = int(np.argmax(hist_high))

        ath_date = dates[ath_index]
        current_date = dates[-1]

        years_since_ath = (current_date - ath_date).days / 365.25

        if years_since_ath < MIN_AGE_YEARS:
            continue

        breakout = current_close > ath_price

        if not breakout:
            continue

        # =========================
        # VOLUME LOGIC
        # =========================

        hist_volume = volume[:-1]
        avg_volume = s(np.mean(hist_volume[-VOLUME_LOOKBACK:]))

        if avg_volume == 0:
            continue

        volume_ratio = current_volume / avg_volume

        if volume_ratio < MIN_VOLUME_RATIO:
            continue

        # =========================
        # RESULT
        # =========================

        results.append(
            f"""
STOCK: {stock}

ATH: {ath_price:.2f}
Close: {current_close:.2f}
ATH Age: {years_since_ath:.1f} years
Volume Spike: {volume_ratio:.2f}x
            """
        )

    except Exception as e:
        print(f"ERROR in {stock}: {e}")

# =========================
# EMAIL
# =========================

body = "\n\n-----------------\n\n".join(results) if results else "No breakouts found."

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
