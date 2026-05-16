import yfinance as yf
import numpy as np
import requests
import os
import smtplib
import time

from email.mime.text import MIMEText
from datetime import datetime

# =========================
# SETTINGS
# =========================

MIN_PRICE = 100
VOLUME_LOOKBACK = 12
MIN_VOLUME_RATIO = 1.8
BATCH_SIZE = 50

EMAIL_ADDRESS = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASS")
TO_EMAIL = os.getenv("EMAIL_TO")

results = []

# =========================
# NSE STOCK UNIVERSE
# =========================

def get_nse_stocks():
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers, timeout=15)
    lines = r.text.splitlines()[1:]

    stocks = []

    for line in lines:
        try:
            symbol = line.split(",")[0].strip()
            if symbol:
                stocks.append(symbol + ".NS")
        except:
            continue

    return list(set(stocks))

# =========================
# SAFE SCALAR
# =========================

def s(x):
    return float(np.asarray(x).squeeze())

# =========================
# SCANNER LOGIC
# =========================

stocks = get_nse_stocks()

print(f"Total stocks loaded: {len(stocks)}")
if len(stocks) == 0:
    print("No stocks loaded - stopping")
    exit()
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

            if df is None or df.empty or len(df) < 60:
                continue

            close = df["Close"].to_numpy()
            high = df["High"].to_numpy()
            volume = df["Volume"].to_numpy()

            current_close = s(close[-1])
            current_volume = s(volume[-1])

            if current_close < MIN_PRICE:
                continue

            # =========================
            # ATH BREAKOUT
            # =========================

            ath_price = s(np.max(high[:-1]))
            breakout = current_close > ath_price

            if not breakout:
                continue

            # =========================
            # VOLUME
            # =========================

            avg_volume = s(np.mean(volume[-VOLUME_LOOKBACK:-1]))

            if avg_volume == 0:
                continue

            volume_ratio = current_volume / avg_volume

            if volume_ratio < MIN_VOLUME_RATIO:
                continue

            # =========================
            # STRENGTH SCORE
            # =========================

            breakout_strength = ((current_close - ath_price) / ath_price) * 100
            breakout_score = min(max(breakout_strength * 2, 0), 30)

            volume_score = min(volume_ratio * 10, 40)

            base_score = 30  # simplified stable base

            score = min(base_score + breakout_score + volume_score, 100)

            if score < 60:
                continue

            if score >= 80:
                quality = "🔥 STRONG BREAKOUT"
            elif score >= 70:
                quality = "⚡ GOOD BREAKOUT"
            else:
                quality = "⚠️ WEAK BREAKOUT"

            results.append(f"""
STOCK: {stock}

ATH Breakout: YES
ATH: {ath_price:.2f}
Close: {current_close:.2f}

Volume Ratio: {volume_ratio:.2f}x
Score: {score:.1f}/100
Quality: {quality}
""")

        except Exception as e:
            print("Error in", stock, e)

    time.sleep(10)  # prevents rate limit

# =========================
# EMAIL OUTPUT
# =========================

body = "\n\n------------------------\n\n".join(results) if results else "No breakouts found."

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
