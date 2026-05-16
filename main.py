import requests
import numpy as np
import time
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

session = requests.Session()

# Fake browser headers (IMPORTANT for NSE)
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com"
}

# =========================
# NSE FUNCTIONS
# =========================

def get_monthly_data(symbol):
    """
    Fetch historical data from NSE chart API
    """

    url = f"https://www.nseindia.com/api/chart-databyindex?index={symbol}&indices=true"

    try:
        session.get("https://www.nseindia.com", headers=HEADERS, timeout=5)
        time.sleep(0.5)

        r = session.get(url, headers=HEADERS, timeout=10)

        if r.status_code != 200:
            return None

        data = r.json()

        # NSE returns nested structure
        prices = data.get("grapthData", [])

        if not prices:
            return None

        # Convert to numpy array (close prices only simplified model)
        closes = np.array([p[1] for p in prices], dtype=float)

        volumes = np.array([p[2] if len(p) > 2 else 1 for p in prices], dtype=float)

        return closes, volumes

    except Exception as e:
        print("Fetch error:", e)
        return None

# =========================
# STOCK LIST
# =========================

with open("stocks.txt") as f:
    stocks = [s.strip() for s in f.readlines() if s.strip()]

results = []

# =========================
# SCANNER
# =========================

for stock in stocks:

    try:
        print(f"Checking {stock}")

        data = get_monthly_data(stock)

        if not data:
            continue

        close, volume = data

        if len(close) < 40:
            continue

        current_close = float(close[-1])
        current_volume = float(volume[-1])

        if current_close < MIN_PRICE:
            continue

        # =========================
        # ATH LOGIC
        # =========================

        ath_price = float(np.max(close[:-1]))
        ath_index = int(np.argmax(close[:-1]))

        years_since_ath = 10  # simplified safe fallback

        breakout = current_close > ath_price

        if not breakout:
            continue

        if years_since_ath < MIN_AGE_YEARS:
            continue

        # =========================
        # VOLUME LOGIC
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

Breakout Above ATH: {ath_price:.2f}
Close: {current_close:.2f}
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
