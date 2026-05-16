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
VOLUME_LOOKBACK = 12
MIN_VOLUME_RATIO = 1.8

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

        current_close = s(close[-1])
        current_volume = s(volume[-1])

        if current_close < MIN_PRICE:
            continue

        # =========================
        # ATH BREAKOUT LOGIC
        # =========================

        hist_high = high[:-1]
        ath_price = s(np.max(hist_high))

        breakout = current_close > ath_price

        if not breakout:
            continue

        # =========================
        # VOLUME SCORE
        # =========================

        avg_volume = s(np.mean(volume[-VOLUME_LOOKBACK:-1]))

        if avg_volume == 0:
            continue

        volume_ratio = current_volume / avg_volume

        # =========================
        # BASE STRENGTH (how long it stayed below ATH)
        # =========================

        base_period = np.where(close[:-1] < ath_price)[0]
        base_length = len(base_period)

        base_score = min(base_length / 60 * 30, 30)  # max 30 points

        # =========================
        # BREAKOUT STRENGTH
        # =========================

        breakout_strength = ((current_close - ath_price) / ath_price) * 100
        breakout_score = min(max(breakout_strength * 2, 0), 30)

        # =========================
        # VOLUME SCORE
        # =========================

        volume_score = min(volume_ratio * 10, 30)

        # =========================
        # VOLATILITY SCORE (lower volatility = better)
        # =========================

        returns = np.diff(close[-12:]) / close[-12:-1]
        volatility = np.std(returns)

        volatility_score = max(20 - volatility * 100, 0)

        # =========================
        # TOTAL SCORE
        # =========================

        score = base_score + breakout_score + volume_score + volatility_score
        score = min(score, 100)

        # =========================
        # FAKE BREAKOUT FILTER
        # =========================

        is_fake = (
            volume_ratio < 1.2 and
            breakout_strength < 2
        )

        if is_fake:
            continue

        # =========================
        # LABEL
        # =========================

        if score >= 75:
            quality = "🔥 STRONG ACCUMULATION BREAKOUT"
        elif score >= 55:
            quality = "⚡ VALID BREAKOUT"
        else:
            quality = "⚠️ WEAK BREAKOUT"

        # =========================
        # RESULT
        # =========================

        results.append(
            f"""
STOCK: {stock}

Breakout Above ATH: YES
ATH: {ath_price:.2f}
Close: {current_close:.2f}

Volume Ratio: {volume_ratio:.2f}x
Breakout Strength: {breakout_strength:.2f}%

SCORE: {score:.1f}/100
QUALITY: {quality}
            """
        )

    except Exception as e:
        print("ERROR in", stock, e)

# =========================
# EMAIL
# =========================

body = "\n\n-----------------\n\n".join(results) if results else "No strong breakouts found."

msg = MIMEText(body)
msg["Subject"] = f"Breakout Strength Scanner - {datetime.now().date()}"
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
