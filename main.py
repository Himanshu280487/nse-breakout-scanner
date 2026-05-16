import yfinance as yf
import pandas as pd
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

        if df is None or df.empty:
            continue

        # FORCE CLEAN SINGLE-LEVEL DATA
        df = df.reset_index()
        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].dropna()

        if len(df) < 40:
            continue

        # =========================
        # CURRENT VALUES (SAFE)
        # =========================

        current_close = float(df["Close"].iloc[-1])
        current_volume = float(df["Volume"].iloc[-1])

        if current_close < MIN_PRICE:
            continue

        # =========================
        # HISTORICAL DATA
        # =========================

        hist = df.iloc[:-1]

        previous_high = float(hist["High"].max())
        previous_high_idx = hist["High"].idxmax()

        current_idx = df.index[-1]

        years_since_high = 3  # fallback safe default

        try:
            years_since_high = (
                (df.loc[current_idx, "Date"] - df.loc[previous_high_idx, "Date"])
                .days / 365.25
            )
        except:
            pass

        # =========================
        # VOLUME
        # =========================

        avg_volume = float(hist["Volume"].tail(VOLUME_LOOKBACK).mean())

        if avg_volume == 0:
            continue

        volume_ratio = current_volume / avg_volume

        # =========================
        # CONDITIONS (FORCED SCALARS ONLY)
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
Level Age: {years_since_high:.1f} years

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
