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
MIN_AGE_YEARS = 3

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

        close = df["Close"].to_numpy()
        high = df["High"].to_numpy()
        volume = df["Volume"].to_numpy()
        dates = df.index

        current_close = float(close[-1])
        current_volume = float(volume[-1])

        if current_close < MIN_PRICE:
            continue

        # =========================
        # ATH LOGIC
        # =========================

        hist_high = high[:-1]
        ath_price = float(np.max(hist_high))
        ath_index = np.argmax(hist_high)

        ath_date = dates[ath_index]
        current_date = dates[-1]

        years_since_ath = (current_date - ath_date).days / 365.25

        if years_since_ath < MIN_AGE_YEARS:
            continue

        breakout = current_close > ath_price

        if not breakout:
            continue

        # =========================
        # VOLUME
        # =========================

        avg_volume = np.mean(volume[-VOLUME_LOOKBACK:-1])

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
Age: {years_since_ath:.1f} years
Volume: {volume_ratio:.2f}x
            """
        )

    except Exception as e:
        print("ERROR in", stock, e)

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
