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
MIN_VOLUME_RATIO = 1.8
VOLUME_LOOKBACK = 12
RECENT_HIGH_LOOKBACK_YEARS = 3  # IMPORTANT NEW RULE

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")

results = []

# =========================
# SAFE SCALAR
# =========================

def s(x):
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

        if df is None or df.empty or len(df) < 60:
            continue

        close = df["Close"].to_numpy()
        high = df["High"].to_numpy()
        volume = df["Volume"].to_numpy()
        dates = df.index

        current_close = s(close[-1])
        current_volume = s(volume[-1])

        if current_close < MIN_PRICE:
            continue

        # =========================
        # TRUE ATH
        # =========================

        hist_high = high[:-1]

        ath_price = s(np.max(hist_high))
        ath_index = int(np.argmax(hist_high))
        ath_date = dates[ath_index]

        current_date = dates[-1]

        # =========================
        # KEY FILTER: RECENT HIGH CHECK
        # =========================

        recent_period = dates[-36] if len(dates) >= 36 else dates[0]
        recent_high = np.max(high[-36:]) if len(high) >= 36 else np.max(high)

        # If stock made ATH or near ATH recently → reject
        near_recent_high = recent_high >= 0.95 * ath_price

        if near_recent_high:
            continue

        # =========================
        # BREAKOUT CONDITION
        # =========================

        breakout = current_close > ath_price

        if not breakout:
            continue

        # =========================
        # VOLUME CONDITION
        # =========================

        avg_volume = s(np.mean(volume[-VOLUME_LOOKBACK:-1]))

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
Volume Spike: {volume_ratio:.2f}x

Status: Multi-year base breakout (no recent highs)
            """
        )

    except Exception as e:
        print("ERROR in", stock, e)

# =========================
# EMAIL
# =========================

body = "\n\n-----------------\n\n".join(results) if results else "No valid breakouts found."

msg = MIMEText(body)
msg["Subject"] = f"Multi-Year Breakout Scanner - {datetime.now().date()}"
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
