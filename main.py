import yfinance as yf
import pandas as pd
import smtplib
import os

from email.mime.text import MIMEText
from datetime import datetime

# =========================================
# SETTINGS
# =========================================

MIN_BREAKOUT_AGE_YEARS = 3
VOLUME_LOOKBACK = 12
MIN_VOLUME_RATIO = 1.8
MIN_PRICE = 100

# =========================================
# EMAIL SETTINGS
# =========================================

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")

# =========================================
# LOAD STOCK LIST
# =========================================

with open("stocks.txt", "r") as f:
    stocks = [line.strip() for line in f.readlines()]

results = []

# =========================================
# SCAN STOCKS
# =========================================

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

        df.dropna(inplace=True)

        # Need enough history
        if len(df) < 36:
            continue

        # Current month data
        current_close = df["Close"].iloc[-1]
        current_volume = df["Volume"].iloc[-1]

        # Ignore cheap stocks
        if current_close < MIN_PRICE:
            continue

        # Exclude current month
        historical_df = df.iloc[:-1]

        # Previous all-time high
        previous_high = historical_df["High"].max()

        # Date of previous ATH
        previous_high_date = historical_df["High"].idxmax()

        # Current candle date
        current_date = df.index[-1]

        # Years since previous ATH
        years_since_high = (
            current_date - previous_high_date
        ).days / 365.25

        # Average volume
        avg_volume = historical_df["Volume"].iloc[
            -VOLUME_LOOKBACK:
        ].mean()

        # Volume ratio
        volume_ratio = current_volume / avg_volume

        # Conditions
        valid_breakout_age = (
            years_since_high >= MIN_BREAKOUT_AGE_YEARS
        )

        breakout = (
            current_close > previous_high
        )

        high_volume = (
            volume_ratio >= MIN_VOLUME_RATIO
        )

        # Final condition
        if (
            valid_breakout_age
            and breakout
            and high_volume
        ):

            results.append(
                f"""
STOCK: {stock}

Breakout Above:
{round(previous_high, 2)}

Breakout Level Age:
{round(years_since_high, 1)} years

Current Close:
{round(current_close, 2)}

Volume Spike:
{round(volume_ratio, 2)}x
                """
            )

    except Exception as e:

        print(f"ERROR in {stock}: {e}")

# =========================================
# EMAIL BODY
# =========================================

if results:

    body = "\n\n====================\n\n".join(results)

else:

    body = "No valid breakout stocks found."

# =========================================
# SEND EMAIL
# =========================================

msg = MIMEText(body)

msg["Subject"] = (
    f"NSE Breakout Scanner "
    f"- {datetime.now().date()}"
)

msg["From"] = EMAIL_ADDRESS
msg["To"] = TO_EMAIL

server = smtplib.SMTP(
    "smtp.gmail.com",
    587
)

server.starttls()

server.login(
    EMAIL_ADDRESS,
    EMAIL_PASSWORD
)

server.send_message(msg)

server.quit()

print("EMAIL SENT SUCCESSFULLY")