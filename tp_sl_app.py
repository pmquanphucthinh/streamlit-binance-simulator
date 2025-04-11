import requests
import pytz
from datetime import datetime, timezone
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

TP_SL_PERCENT = 0.022

st.set_page_config(page_title="TP/SL Tracker", layout="centered")
st.title("\ud83d\udcc8 TP/SL Tracker (\u00b12.2%)")

symbol_input = st.text_input("Nhập tên coin (VD: BTC):", value="BTC")
time_input = st.text_input("Giờ vào lệnh (VD: 14:30):", value="14:30")

if st.button("Phân tích"):
    try:
        symbol = symbol_input.upper() + "USDT" if not symbol_input.upper().endswith("USDT") else symbol_input.upper()
        today = datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")).strftime('%Y-%m-%d')
        entry_time_str = f"{today} {time_input}:00"
        entry_time_local = datetime.strptime(entry_time_str, "%Y-%m-%d %H:%M:%S")
        entry_time_utc = pytz.timezone("Asia/Ho_Chi_Minh").localize(entry_time_local).astimezone(timezone.utc)

        target_ts = int(entry_time_utc.timestamp() * 1000)
        now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        minutes_diff = int((now_ts - target_ts) / 60000)
        limit = min(minutes_diff + 1, 1000)

        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit={limit}"
        res = requests.get(url)
        if res.status_code != 200:
            st.error(f"Lỗi khi lấy dữ liệu: {res.status_code}")
            st.stop()

        klines = res.json()

        entry_price = None
        for k in klines:
            if int(k[0]) <= target_ts < int(k[0]) + 60000:
                entry_price = float(k[1])
                break

        if entry_price is None:
            st.warning("\u274c Không tìm thấy giá vào lệnh.")
            st.stop()

        tp_price = entry_price * (1 + TP_SL_PERCENT)
        sl_price = entry_price * (1 - TP_SL_PERCENT)

        hit_idx = None
        result = "\u23f3 CHƯA CHẠM TP/SL"
        for idx, k in enumerate(klines):
            high = float(k[2])
            low = float(k[3])
            if high >= tp_price:
                result = "\ud83d\udd35 TĂNG 2.2% TRƯỜC"
                hit_idx = idx
                break
            if low <= sl_price:
                result = "\ud83d\udd34 GIẢM 2.2% TRƯỜC"
                hit_idx = idx
                break

        current_price = float(klines[-1][4])
        st.success(f"**{result}**\n\nGiá vào: `{entry_price:.4f}` | Hiện tại: `{current_price:.4f}`")

        # Vẽ biểu đồ
        times = [datetime.fromtimestamp(k[0]/1000) for k in klines]
        closes = [float(k[4]) for k in klines]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(times, closes, label='Giá đóng cửa', color='blue')
        ax.axhline(entry_price, color='gray', linestyle='--', label=f'Entry ({entry_price:.4f})')
        ax.axhline(tp_price, color='green', linestyle='--', label=f'TP ({tp_price:.4f})')
        ax.axhline(sl_price, color='red', linestyle='--', label=f'SL ({sl_price:.4f})')

        if hit_idx is not None:
            hit_time = datetime.fromtimestamp(klines[hit_idx][0]/1000)
            hit_price = float(klines[hit_idx][4])
            ax.plot(hit_time, hit_price, 'ro', label="Chạm TP/SL")

        ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
        ax.set_title("Biểu đồ TP/SL ±2.2%")
        ax.set_xlabel("Thời gian")
        ax.set_ylabel("Giá USDT")
        ax.grid(True)
        ax.legend()
        st.pyplot(fig)

    except Exception as ex:
        st.error(f"\u274c Lỗi: {str(ex)}")
