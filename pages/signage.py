"""
ビジネス講義室予約システム — サイネージ表示ページ
パスワード不要・自動更新・大画面向け表示
"""

import streamlit as st
import pandas as pd
import os
from datetime import date, datetime
import time

# ═════════════════════════════════════════════════════════════════
# 定数
# ═════════════════════════════════════════════════════════════════
CSV_FILE   = "reservations.csv"
TIME_SLOTS = ["1限", "2限", "3限", "4限", "5限", "昼休み", "放課後"]
COLUMNS    = ["日付", "時間帯", "学年", "氏名", "使用目的", "備考", "登録日時"]
WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

# 自動更新の間隔（秒）
REFRESH_INTERVAL = 60

# ═════════════════════════════════════════════════════════════════
# ページ設定
# ═════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="講義室 本日の予約状況",
    page_icon="🏫",
    layout="wide",
)

# ═════════════════════════════════════════════════════════════════
# スタイル
# ═════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700;900&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans JP', sans-serif;
    background-color: #0f172a;
    color: #f1f5f9;
}

/* ─── ヘッダー ─── */
.signage-header {
    text-align: center;
    padding: 24px 0 16px 0;
}
.signage-title {
    font-size: 2rem;
    font-weight: 700;
    color: #94a3b8;
    letter-spacing: 0.1em;
    margin-bottom: 4px;
}
.signage-date {
    font-size: 3.5rem;
    font-weight: 900;
    color: #f1f5f9;
    line-height: 1.1;
}
.signage-updated {
    font-size: 0.85rem;
    color: #64748b;
    margin-top: 6px;
}

/* ─── 時間帯カード ─── */
.slot-row {
    display: flex;
    align-items: stretch;
    margin-bottom: 12px;
    border-radius: 14px;
    overflow: hidden;
    min-height: 90px;
}

/* 時間帯ラベル */
.slot-time {
    width: 130px;
    min-width: 130px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    font-weight: 900;
    background: #1e293b;
    color: #cbd5e1;
    letter-spacing: 0.05em;
}

/* 空きセル */
.slot-free {
    flex: 1;
    display: flex;
    align-items: center;
    padding: 16px 28px;
    background: #14532d;
    border-left: 6px solid #22c55e;
}
.slot-free-label {
    font-size: 2rem;
    font-weight: 700;
    color: #4ade80;
    letter-spacing: 0.1em;
}

/* 予約ありセル */
.slot-taken {
    flex: 1;
    display: flex;
    align-items: center;
    padding: 16px 28px;
    background: #450a0a;
    border-left: 6px solid #ef4444;
    gap: 24px;
}
.slot-taken-badge {
    font-size: 1.4rem;
    font-weight: 700;
    color: #fca5a5;
    white-space: nowrap;
}
.slot-taken-detail {
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.slot-taken-name {
    font-size: 1.8rem;
    font-weight: 900;
    color: #fef2f2;
    line-height: 1.1;
}
.slot-taken-purpose {
    font-size: 1.1rem;
    color: #fca5a5;
}
</style>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════
# CSV 読み込み
# ═════════════════════════════════════════════════════════════════
def load_csv() -> pd.DataFrame:
    if not os.path.exists(CSV_FILE):
        return pd.DataFrame(columns=COLUMNS)
    try:
        return pd.read_csv(CSV_FILE, encoding="utf-8-sig", dtype=str).fillna("")
    except Exception:
        return pd.DataFrame(columns=COLUMNS)

def get_reserved_slots(df: pd.DataFrame, target_date: str) -> dict:
    day_df = df[df["日付"] == target_date]
    return {row["時間帯"]: row for _, row in day_df.iterrows()}

# ═════════════════════════════════════════════════════════════════
# メイン表示
# ═════════════════════════════════════════════════════════════════
today      = date.today()
today_str  = today.strftime("%Y-%m-%d")
weekday    = WEEKDAY_JP[today.weekday()]
now_str    = datetime.now().strftime("%H:%M")

# ヘッダー
st.markdown(
    f'<div class="signage-header">'
    f'<div class="signage-title">🏫 ビジネス講義室　本日の予約状況</div>'
    f'<div class="signage-date">'
    f'{today.year}年{today.month}月{today.day}日（{weekday}）'
    f'</div>'
    f'<div class="signage-updated">最終更新：{now_str}　／　{REFRESH_INTERVAL}秒ごとに自動更新</div>'
    f'</div>',
    unsafe_allow_html=True,
)

st.markdown("---")

# 予約データ取得
df       = load_csv()
reserved = get_reserved_slots(df, today_str)

# 時間帯ごとに表示
for slot in TIME_SLOTS:
    if slot in reserved:
        r       = reserved[slot]
        name    = r.get("氏名", "")
        grade   = r.get("学年", "")
        purpose = r.get("使用目的", "")
        st.markdown(
            f'<div class="slot-row">'
            f'  <div class="slot-time">{slot}</div>'
            f'  <div class="slot-taken">'
            f'    <div class="slot-taken-badge">🔴 予約あり</div>'
            f'    <div class="slot-taken-detail">'
            f'      <div class="slot-taken-name">{grade}　{name}</div>'
            f'      <div class="slot-taken-purpose">📌 {purpose}</div>'
            f'    </div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="slot-row">'
            f'  <div class="slot-time">{slot}</div>'
            f'  <div class="slot-free">'
            f'    <div class="slot-free-label">🟢　空き</div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ═════════════════════════════════════════════════════════════════
# 自動更新
# ═════════════════════════════════════════════════════════════════
time.sleep(REFRESH_INTERVAL)
st.rerun()
