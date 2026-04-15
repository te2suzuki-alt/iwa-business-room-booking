import streamlit as st
import pandas as pd
import os
from datetime import date, datetime
import time

CSV_FILE   = "reservations.csv"
TIME_SLOTS = ["1限", "2限", "3限", "4限", "5限", "昼休み", "放課後"]
COLUMNS    = ["日付", "時間帯", "学年", "氏名", "使用目的", "備考", "登録日時"]
WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]
REFRESH_INTERVAL = 60

st.session_state["is_logged_in"] = True

st.set_page_config(
    page_title="講義室 本日の予約状況",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="stSidebar"]        { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
html, body, [class*="css"] {
    font-family: 'Noto Sans JP', sans-serif;
    background-color: #0f172a !important;
    color: #f1f5f9;
}
.stApp { background-color: #0f172a !important; }
.signage-header { text-align:center; padding:24px 0 16px 0; }
.signage-title  { font-size:2rem; font-weight:700; color:#94a3b8; letter-spacing:0.1em; margin-bottom:4px; }
.signage-date   { font-size:3.5rem; font-weight:900; color:#f1f5f9; line-height:1.1; }
.signage-updated { font-size:0.85rem; color:#64748b; margin-top:6px; }
.slot-row { display:flex; align-items:stretch; margin-bottom:12px; border-radius:14px; overflow:hidden; min-height:90px; }
.slot-time { width:130px; min-width:130px; display:flex; align-items:center; justify-content:center; font-size:1.5rem; font-weight:900; background:#1e293b; color:#cbd5e1; }
.slot-free { flex:1; display:flex; align-items:center; padding:16px 28px; background:#14532d; border-left:6px solid #22c55e; }
.slot-free-label { font-size:2rem; font-weight:700; color:#4ade80; }
.slot-taken { flex:1; display:flex; align-items:center; padding:16px 28px; background:#450a0a; border-left:6px solid #ef4444; gap:24px; }
.slot-taken-badge { font-size:1.4rem; font-weight:700; color:#fca5a5; white-space:nowrap; }
.slot-taken-detail { display:flex; flex-direction:column; gap:4px; }
.slot-taken-name { font-size:1.8rem; font-weight:900; color:#fef2f2; line-height:1.1; }
.slot-taken-purpose { font-size:1.1rem; color:#fca5a5; }
</style>
""", unsafe_allow_html=True)

def load_csv():
    if not os.path.exists(CSV_FILE):
        return pd.DataFrame(columns=COLUMNS)
    try:
        return pd.read_csv(CSV_FILE, encoding="utf-8-sig", dtype=str).fillna("")
    except Exception:
        return pd.DataFrame(columns=COLUMNS)

today     = date.today()
today_str = today.strftime("%Y-%m-%d")
weekday   = WEEKDAY_JP[today.weekday()]
now_str   = datetime.now().strftime("%H:%M")

st.markdown(
    f'<div class="signage-header">'
    f'<div class="signage-title">🏫 ビジネス講義室　本日の予約状況</div>'
    f'<div class="signage-date">{today.year}年{today.month}月{today.day}日（{weekday}）</div>'
    f'<div class="signage-updated">最終更新：{now_str}　／　{REFRESH_INTERVAL}秒ごとに自動更新</div>'
    f'</div>',
    unsafe_allow_html=True,
)
st.markdown("---")

df = load_csv()
day_df = df[df["日付"] == today_str]
reserved = {row["時間帯"]: row for _, row in day_df.iterrows()}

for slot in TIME_SLOTS:
    if slot in reserved:
        r = reserved[slot]
        st.markdown(
            f'<div class="slot-row">'
            f'<div class="slot-time">{slot}</div>'
            f'<div class="slot-taken">'
            f'<div class="slot-taken-badge">🔴 予約あり</div>'
            f'<div class="slot-taken-detail">'
            f'<div class="slot-taken-name">{r.get("学年","")}　{r.get("氏名","")}</div>'
            f'<div class="slot-taken-purpose">📌 {r.get("使用目的","")}</div>'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="slot-row">'
            f'<div class="slot-time">{slot}</div>'
            f'<div class="slot-free"><div class="slot-free-label">🟢　空き</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

time.sleep(REFRESH_INTERVAL)
st.rerun()
