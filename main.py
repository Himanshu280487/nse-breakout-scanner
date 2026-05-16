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

# =========================
# EMAIL CONFIG (Railway ENV)
# =========================

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")

# =========================
# LOAD STOCK LIST
# =========================

with open("stocks.txt", "r") as f:
    stocks = [line.strip() for line in f.readlines() if line.strip()]

results = []

# =========================
# SCANNER
# =========================

for stock in stocks:

    try:
        print(f"Checking {stock}")

        # Download monthly data
        df = yf.download(
            stock,
            period="max",
            interval="1mo",
            auto_adjust=True,
            progress=False
        )

        if df is None or df.empty:
            continue

        # Keep only needed columns
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()

        if len(df) < 40:
            continue

        # =========================
        # CURRENT DATA (SAFE SCALARS)
        # =========================

        current_close = float(df["Close"].iat[-1])
        current_volume = float(df["Volume"].iat[-1])

        if current_close < MIN_PRICE:
            continue

        # =========================
        # HISTORICAL DATA
        # =========================

        historical_df = df.iloc[:-1]

        previous_high = float(historical_df["High"].max())
        previous_high_date = historical_df["High"].idxmax()

        current_date = df.index[-1]

        years_since_high = (
            current_date - previous_high_date
        ).days / 365.25

        # =========================
        # VOLUME LOGIC
        # =========================

        avg_volume = float(
            historical_df["Volume"]
            .tail(VOLUME_LOOKBACK)
            .mean()
        )

        if avg_volume == 0:
            continue

        volume_ratio = current_volume / avg_volume

        # =========================
        # CONDITIONS
        # =========================

        breakout = current_close > previous_high

        valid_age = years_since_high >= MIN_BREAKOUT_AGE_YEARS

        high_volume = volume_ratio >= MIN_VOLUME_RATIO

        # =========================
        # FINAL FILTER
        # =========================

        if breakout and valid_age and high_volume:

            results.append(
                f"""
STOCK: {stock}

Breakout Level: {round(previous_high, 2)}
Level Age: {round(years_since_high, 1)} years

Current Close: {round(current_close, 2)}
Volume Spike: {round(volume_ratio, 2)}x
                """
            )

    except Exception as e:
        print(f"ERROR in {stock}: {e}")

# =========================
# EMAIL CONTENT
# =========================

if results:
    body = "\n\n---------------------\n\n".join(results)
else:
    body = "No valid breakout stocks found today."

msg = MIMEText(body)

msg["Subject"] = f"NSE Breakout Scanner - {datetime.now().date()}"
msg["From"] = EMAIL_ADDRESS
msg["To"] = TO_EMAIL

# =========================
# SEND EMAIL
# =========================

try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()

    print("EMAIL SENT SUCCESSFULLY")

except Exception as e:
    print("EMAIL ERROR:", e)
