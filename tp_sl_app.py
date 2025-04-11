import requests
import pytz
from datetime import datetime, timezone
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

TP_SL_PERCENT = 0.022

st.set_page_config(page_title="TP/SL Tracker", layout="centered")
st.title("TP/SL Tracker (+/-2.2%)")

symbol_input = st.text_input("Enter coin symbol (e.g., BTC):", value="BTC")
time_input = st.text_input("Entry time (e.g., 14:30):", value="14:30")

if st.button("Analyze"):
    try:
        symbol = symbol_input.upper() + "USDT" if not symbol_input.upper().endswith("USDT") else symbol_input.upper()
        today = datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")).strftime('%Y-%m-%d')
        entry_time_str = f"{today} {time_input}:00"
        entry_time_local = datetime.strptime(entry_time_str, "%Y-%m-%d %H:%M:%S")
        entry_time_utc = pytz.timezone("Asia/Ho_Chi_Minh").localize(entry_time_local).astimezone(timezone.utc)

        # Use CoinGecko OHLC endpoint as alternative to Binance
        coingecko_id = symbol.replace("USDT", "").lower()
        url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}/ohlc?vs_currency=usd&days=1"
        res = requests.get(url)
        if res.status_code != 200:
            st.error(f"Failed to fetch data: {res.status_code}")
            st.stop()

        ohlc_data = res.json()
        if not ohlc_data:
            st.warning("No OHLC data found.")
            st.stop()

        # Convert OHLC to matching format (timestamp, open, high, low, close)
        klines = [[int(k[0]), k[1], k[2], k[3], k[4]] for k in ohlc_data]

        target_ts = int(entry_time_utc.timestamp() * 1000)
        entry_price = None
        for k in klines:
            if int(k[0]) <= target_ts < int(k[0]) + 60000:
                entry_price = float(k[1])
                break

        if entry_price is None:
            st.warning("Entry price not found.")
            st.stop()

        tp_price = entry_price * (1 + TP_SL_PERCENT)
        sl_price = entry_price * (1 - TP_SL_PERCENT)

        hit_idx = None
        result = "Not hit TP/SL yet"
        for idx, k in enumerate(klines):
            high = float(k[2])
            low = float(k[3])
            if high >= tp_price:
                result = "Hit Take Profit first"
                hit_idx = idx
                break
            if low <= sl_price:
                result = "Hit Stop Loss first"
                hit_idx = idx
                break

        current_price = float(klines[-1][4])
        st.success(f"**{result}**\n\nEntry price: `{entry_price:.4f}` | Current price: `{current_price:.4f}`")

        # Plot chart
        times = [datetime.fromtimestamp(k[0]/1000) for k in klines]
        closes = [float(k[4]) for k in klines]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(times, closes, label='Close Price', color='blue')
        ax.axhline(entry_price, color='gray', linestyle='--', label=f'Entry ({entry_price:.4f})')
        ax.axhline(tp_price, color='green', linestyle='--', label=f'TP ({tp_price:.4f})')
        ax.axhline(sl_price, color='red', linestyle='--', label=f'SL ({sl_price:.4f})')

        if hit_idx is not None:
            hit_time = datetime.fromtimestamp(klines[hit_idx][0]/1000)
            hit_price = float(klines[hit_idx][4])
            ax.plot(hit_time, hit_price, 'ro', label="Hit TP/SL")

        ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
        ax.set_title("TP/SL Chart ±2.2%")
        ax.set_xlabel("Time")
        ax.set_ylabel("Price (USDT)")
        ax.grid(True)
        ax.legend()
        st.pyplot(fig)

    except Exception as ex:
        st.error(f"Error: {str(ex)}")
