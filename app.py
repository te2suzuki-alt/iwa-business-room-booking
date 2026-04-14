"""
ビジネス講義室予約システム — app.py
認証方式：パスワード認証（学内共有パスワード）
"""

import streamlit as st
import pandas as pd
import os
from datetime import date, datetime, timedelta

# ═════════════════════════════════════════════════════════════════
# 定数
# ═════════════════════════════════════════════════════════════════
CSV_FILE       = "reservations.csv"
APP_PASSWORD   = st.secrets["APP_PASSWORD"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
TIME_SLOTS     = ["1限", "2限", "3限", "4限", "5限", "昼休み", "放課後"]
GRADES         = ["1年", "2年", "3年", "4年"]
COLUMNS        = ["日付", "時間帯", "学年", "氏名", "使用目的", "備考", "登録日時"]
WEEKDAY_JP     = ["月", "火", "水", "木", "金", "土", "日"]

# ═════════════════════════════════════════════════════════════════
# ページ設定（必ず最初に呼ぶ）
# ═════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="ビジネス講義室予約システム",
    page_icon="🏫",
    layout="wide",
)

# ═════════════════════════════════════════════════════════════════
# session_state の初期化
# ═════════════════════════════════════════════════════════════════
if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False
if "flash_message" not in st.session_state:
    st.session_state["flash_message"] = None

# ═════════════════════════════════════════════════════════════════
# グローバルスタイル
# ═════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }

/* ─── ログイン画面 ─── */
.login-wrap { display:flex; justify-content:center; margin-top:80px; }
.login-box {
    width:100%; max-width:420px;
    padding:44px 40px;
    border-radius:18px;
    background:#ffffff;
    box-shadow:0 4px 32px rgba(0,0,0,0.10);
    text-align:center;
}
.login-icon  { font-size:3rem; margin-bottom:10px; }
.login-title { font-size:1.55rem; font-weight:700; color:#1a3a5c; margin-bottom:6px; }
.login-sub   { font-size:0.88rem; color:#6b7280; margin-bottom:24px; line-height:1.6; }

/* ─── ヘッダー ─── */
.main-title {
    font-size:2rem; font-weight:700; color:#1a3a5c;
    border-bottom:3px solid #2e7bcf;
    padding-bottom:0.3rem; margin-bottom:0.2rem;
}
.sub-title { color:#6b7280; font-size:0.95rem; margin-bottom:0.8rem; }

/* ─── 予約状況カード ─── */
.slot-card {
    border-radius:10px; padding:14px 18px; margin-bottom:10px;
    font-size:0.93rem; border-left:5px solid; line-height:1.7;
}
.slot-free  { background:#f0fdf4; border-color:#22c55e; color:#166534; }
.slot-taken { background:#fff1f2; border-color:#ef4444; color:#7f1d1d; }
.slot-label { font-weight:700; font-size:1.05rem; }

/* ─── 管理者バッジ ─── */
.admin-badge {
    display:inline-block; background:#1a3a5c; color:#fff;
    border-radius:20px; padding:2px 14px;
    font-size:0.8rem; font-weight:600;
    margin-left:10px; vertical-align:middle;
}

/* ─── カレンダー ─── */
.cal-wrapper {
    overflow-x:auto; margin-top:8px;
    border-radius:10px; box-shadow:0 2px 12px rgba(0,0,0,0.08);
}
.cal-table { width:100%; border-collapse:collapse; font-size:0.85rem; min-width:680px; }
.cal-th {
    background:#1a3a5c; color:#fff; text-align:center;
    padding:10px 6px; font-weight:600; white-space:nowrap;
    border:1px solid #14304f;
}
.cal-corner         { background:#0f2540; }
.cal-today-header   { background:#2e7bcf; }
.cal-weekend-header { background:#3d5a80; }
.cal-date    { font-size:1rem; font-weight:700; }
.cal-weekday { font-size:0.75rem; opacity:0.85; }
.cal-slot-label {
    background:#f1f5f9; color:#1a3a5c; font-weight:700;
    text-align:center; padding:10px; white-space:nowrap;
    border:1px solid #e2e8f0; min-width:56px;
}
.cal-cell {
    text-align:center; vertical-align:middle;
    padding:8px 6px; border:1px solid #e2e8f0;
    min-width:90px; height:58px;
}
.cal-free              { background:#f8fafc; }
.cal-free-label        { color:#94a3b8; font-size:0.82rem; }
.cal-today-col.cal-free   { background:#eff8ff; }
.cal-weekend-col.cal-free { background:#fafafa; }
.cal-taken             { background:#fff1f2; }
.cal-today-col.cal-taken  { background:#fef3c7; }
.cal-name {
    font-weight:700; color:#be123c; font-size:0.88rem;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:100px;
}
.cal-today-col .cal-name    { color:#92400e; }
.cal-purpose {
    font-size:0.75rem; color:#9f1239;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:100px;
}
.cal-today-col .cal-purpose { color:#b45309; }
.cal-today-col {
    border-left:2px solid #2e7bcf !important;
    border-right:2px solid #2e7bcf !important;
}
</style>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════
# ── ログイン画面（未ログイン時のみ表示）──
# ═════════════════════════════════════════════════════════════════
if not st.session_state["is_logged_in"]:

    st.markdown("""
<div class="login-wrap">
  <div class="login-box">
    <div class="login-icon">🏫</div>
    <div class="login-title">ビジネス講義室予約システム</div>
    <div class="login-sub">学内共有パスワードを入力してください</div>
  </div>
</div>
""", unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        pwd = st.text_input("パスワード", type="password", key="login_pwd")
        if st.button("ログイン", type="primary", use_container_width=True):
            if pwd == APP_PASSWORD:
                st.session_state["is_logged_in"] = True
                st.session_state["flash_message"] = {
                    "type": "success", "text": "ログインしました"
                }
                st.rerun()
            else:
                st.error("❌ パスワードが違います")

    st.stop()   # ログインするまでここより下を表示しない

# ─── ここより下はログイン済みユーザーのみ到達 ───────────────────

# ═════════════════════════════════════════════════════════════════
# CSV 読み書き
# ═════════════════════════════════════════════════════════════════
def load_csv() -> pd.DataFrame:
    if not os.path.exists(CSV_FILE):
        df_empty = pd.DataFrame(columns=COLUMNS)
        try:
            df_empty.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
        except Exception as e:
            st.warning(f"CSVファイルの作成に失敗しました: {e}")
            return df_empty
    try:
        return pd.read_csv(CSV_FILE, encoding="utf-8-sig", dtype=str).fillna("")
    except Exception as e:
        st.error(f"CSVの読み込みに失敗しました: {e}")
        return pd.DataFrame(columns=COLUMNS)

def save_csv(df: pd.DataFrame) -> None:
    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

# ═════════════════════════════════════════════════════════════════
# ヘルパー関数
# ═════════════════════════════════════════════════════════════════
def get_reserved_slots(df: pd.DataFrame, target_date: str) -> dict:
    day_df = df[df["日付"] == target_date]
    return {row["時間帯"]: row for _, row in day_df.iterrows()}

def is_slot_taken(target_date: str, slot: str) -> bool:
    latest_df = load_csv()
    return not latest_df[
        (latest_df["日付"] == target_date) & (latest_df["時間帯"] == slot)
    ].empty

def check_admin() -> bool:
    return st.session_state.get("is_admin", False)

def build_calendar_html(df: pd.DataFrame, today: date) -> str:
    days = [today + timedelta(days=i) for i in range(7)]
    reservation_map: dict = {}
    for _, row in df.iterrows():
        reservation_map[(row["日付"], row["時間帯"])] = row

    header_cells = '<th class="cal-th cal-corner">時間帯</th>'
    for d in days:
        d_str      = d.strftime("%Y-%m-%d")
        m_d        = f"{d.month}/{d.day}"
        weekday    = WEEKDAY_JP[d.weekday()]
        is_today   = (d == today)
        is_weekend = d.weekday() >= 5
        if is_today:
            th_class = "cal-th cal-today-header"
        elif is_weekend:
            th_class = "cal-th cal-weekend-header"
        else:
            th_class = "cal-th"
        header_cells += (
            f'<th class="{th_class}">'
            f'<div class="cal-date">{m_d}</div>'
            f'<div class="cal-weekday">({weekday})</div>'
            f'</th>'
        )

    body_rows = ""
    for slot in TIME_SLOTS:
        row_html = f'<td class="cal-slot-label">{slot}</td>'
        for d in days:
            d_str      = d.strftime("%Y-%m-%d")
            is_today   = (d == today)
            is_weekend = d.weekday() >= 5
            res        = reservation_map.get((d_str, slot))
            if res is not None:
                name    = res.get("氏名", "")
                purpose = res.get("使用目的", "")
                cls     = "cal-cell cal-taken" + (" cal-today-col" if is_today else "")
                row_html += (
                    f'<td class="{cls}">'
                    f'<div class="cal-name">{name}</div>'
                    f'<div class="cal-purpose">{purpose}</div>'
                    f'</td>'
                )
            else:
                cls = "cal-cell cal-free"
                if is_today:
                    cls += " cal-today-col"
                elif is_weekend:
                    cls += " cal-weekend-col"
                row_html += f'<td class="{cls}"><span class="cal-free-label">空き</span></td>'
        body_rows += f"<tr>{row_html}</tr>"

    return f"""
<div class="cal-wrapper">
  <table class="cal-table">
    <thead><tr>{header_cells}</tr></thead>
    <tbody>{body_rows}</tbody>
  </table>
</div>
"""

# ═════════════════════════════════════════════════════════════════
# サイドバー
# ═════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🏫 メニュー")
    page = st.radio(
        "画面を選択",
        ["📅 予約・閲覧", "🔧 管理者画面"],
        label_visibility="collapsed",
    )

    # ── ログアウト ──
    st.markdown("---")
    if st.button("🚪 ログアウト", use_container_width=True):
        st.session_state["is_logged_in"] = False
        st.session_state["is_admin"] = False
        st.rerun()

    # ── 管理者パスワード認証 ──
    st.markdown("---")
    st.markdown("### 🔑 管理者ログイン")
    if not check_admin():
        pwd_input = st.text_input("管理者パスワード", type="password", key="pwd_input")
        if st.button("管理者ログイン", key="admin_login_btn"):
            if pwd_input == ADMIN_PASSWORD:
                st.session_state["is_admin"] = True
                st.session_state["flash_message"] = {
                    "type": "success", "text": "管理者としてログインしました"
                }
                st.rerun()
            else:
                st.error("パスワードが違います")
    else:
        st.success("管理者としてログイン中")
        st.markdown('<span class="admin-badge">ADMIN</span>', unsafe_allow_html=True)
        if st.button("管理者ログアウト", key="admin_logout_btn"):
            st.session_state["is_admin"] = False
            st.session_state["flash_message"] = {
                "type": "success", "text": "管理者をログアウトしました"
            }
            st.rerun()

# ═════════════════════════════════════════════════════════════════
# メインエリア：タイトル
# ═════════════════════════════════════════════════════════════════
st.markdown('<div class="main-title">🏫 ビジネス講義室予約システム</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">ビジネス講義室 ／ 予約は当日を含む7日先まで可能</div>', unsafe_allow_html=True)

# フラッシュメッセージ
flash = st.session_state.get("flash_message")
if flash:
    if flash["type"] == "success":
        st.success(flash["text"])
    elif flash["type"] == "error":
        st.error(flash["text"])
    elif flash["type"] == "warning":
        st.warning(flash["text"])
    st.session_state["flash_message"] = None

df = load_csv()

# ═════════════════════════════════════════════════════════════════
# 画面①：予約・閲覧
# ═════════════════════════════════════════════════════════════════
if page == "📅 予約・閲覧":

    col_left, col_right = st.columns([1, 1], gap="large")

    # ── 左：予約状況カード ──
    with col_left:
        st.subheader("📋 予約状況（日別）")
        selected_date = st.date_input("日付を選択", value=date.today(), key="view_date")
        date_str = selected_date.strftime("%Y-%m-%d")
        reserved = get_reserved_slots(df, date_str)

        st.markdown(f"**{selected_date.strftime('%Y年%m月%d日')} の予約状況**")
        for slot in TIME_SLOTS:
            if slot in reserved:
                r = reserved[slot]
                st.markdown(
                    f'<div class="slot-card slot-taken">'
                    f'<span class="slot-label">🔴 {slot}</span>　予約あり<br>'
                    f'👤 {r["学年"]}　{r["氏名"]}<br>'
                    f'📌 {r["使用目的"]}'
                    f'{"　💬 " + r["備考"] if r["備考"] else ""}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="slot-card slot-free">'
                    f'<span class="slot-label">🟢 {slot}</span>　空き'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── 右：予約登録 ──
    with col_right:
        st.subheader("✍️ 予約登録")

        with st.form("reserve_form", clear_on_submit=True):
            f_date = st.date_input("予約日", value=date.today(), key="f_date")
            f_date_str = f_date.strftime("%Y-%m-%d")
            reserved_for_form = get_reserved_slots(df, f_date_str)
            free_slots = [s for s in TIME_SLOTS if s not in reserved_for_form]

            if free_slots:
                f_slot    = st.selectbox("時間帯", free_slots)
                f_grade   = st.selectbox("学年", GRADES)
                f_name    = st.text_input("氏名 *")
                f_purpose = st.text_input("使用目的 *")
                f_note    = st.text_input("備考（任意）")
                submitted = st.form_submit_button(
                    "📝 予約する", type="primary", use_container_width=True
                )

                if submitted:
                    if not f_name.strip():
                        st.error("❌ 氏名を入力してください")
                    elif not f_purpose.strip():
                        st.error("❌ 使用目的を入力してください")
                    else:
                        if is_slot_taken(f_date_str, f_slot):
                            st.session_state["flash_message"] = {
                                "type": "error",
                                "text": (
                                    f"⚠️ {f_date_str}（{f_slot}）は直前に別の予約が入りました。"
                                    "別の時間帯を選んでください。"
                                ),
                            }
                            st.rerun()
                        else:
                            new_row = pd.DataFrame([{
                                "日付":     f_date_str,
                                "時間帯":   f_slot,
                                "学年":     f_grade,
                                "氏名":     f_name.strip(),
                                "使用目的": f_purpose.strip(),
                                "備考":     f_note.strip(),
                                "登録日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            }])
                            updated_df = pd.concat([load_csv(), new_row], ignore_index=True)
                            save_csv(updated_df)
                            st.session_state["flash_message"] = {
                                "type": "success",
                                "text": f"✅ {f_date_str}（{f_slot}）の予約が完了しました！",
                            }
                            st.rerun()
            else:
                st.warning("この日はすべての時間帯が予約済みです。")
                st.form_submit_button("予約する", disabled=True, use_container_width=True)

        # ── キャンセル（管理者のみ）──
        st.markdown("---")
        st.subheader("🗑️ 予約キャンセル")

        if check_admin():
            c_date = st.date_input("キャンセルする日付", value=date.today(), key="cancel_date")
            c_date_str = c_date.strftime("%Y-%m-%d")
            latest_df_for_cancel = load_csv()
            reserved_c  = get_reserved_slots(latest_df_for_cancel, c_date_str)
            taken_slots = list(reserved_c.keys())

            if taken_slots:
                c_slot = st.selectbox("キャンセルする時間帯", taken_slots, key="cancel_slot")
                c_row  = reserved_c.get(c_slot)
                if c_row is not None:
                    st.info(
                        f"予約者：{c_row.get('学年', '')}　{c_row.get('氏名', '')}　"
                        f"／　{c_row.get('使用目的', '')}"
                    )
                with st.form("cancel_form"):
                    st.caption(f"上記の予約（{c_date_str} / {c_slot}）をキャンセルします")
                    c_submit = st.form_submit_button(
                        "❌ キャンセル実行", type="primary", use_container_width=True
                    )
                    if c_submit:
                        df_before = load_csv()
                        df_after  = df_before[
                            ~((df_before["日付"] == c_date_str) & (df_before["時間帯"] == c_slot))
                        ]
                        save_csv(df_after)
                        st.session_state["flash_message"] = {
                            "type": "success",
                            "text": f"🗑️ {c_date_str}（{c_slot}）の予約をキャンセルしました",
                        }
                        st.rerun()
            else:
                st.info("この日に予約はありません")
        else:
            st.info("🔒 予約のキャンセルは管理者のみ可能です。サイドバーからログインしてください。")

    # ── 週間カレンダー ──
    st.markdown("---")
    st.subheader("📆 週間カレンダー（当日〜7日間）")

    cal_col1, _ = st.columns([1, 3])
    with cal_col1:
        cal_start = st.date_input(
            "表示開始日",
            value=date.today(),
            key="cal_start_date",
            help="この日を含む7日間を表示します",
        )

    cal_df   = load_csv()
    cal_html = build_calendar_html(cal_df, cal_start)

    st.markdown(
        '<div style="font-size:0.82rem; color:#64748b; margin-bottom:4px;">'
        '　🟦 <b>今日列</b>（青枠）　　'
        '🟩 <b>空き</b>（薄グレー）　　'
        '🟥 <b>予約あり</b>（ピンク）　　'
        '氏名と使用目的を表示'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(cal_html, unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════
# 画面②：管理者画面
# ═════════════════════════════════════════════════════════════════
elif page == "🔧 管理者画面":
    if not check_admin():
        st.warning("🔒 管理者画面にアクセスするにはサイドバーからログインしてください。")
        st.stop()

    st.subheader("🔧 管理者画面 — 全予約一覧")
    df_admin = load_csv()

    col_f1, col_f2, _ = st.columns([1, 1, 2])
    with col_f1:
        filter_mode = st.radio("絞り込み", ["全件表示", "日付指定"], horizontal=True)
    with col_f2:
        if filter_mode == "日付指定":
            filter_date     = st.date_input("日付", value=date.today(), key="admin_date")
            filter_date_str = filter_date.strftime("%Y-%m-%d")
            display_df = df_admin[df_admin["日付"] == filter_date_str].copy()
        else:
            display_df = df_admin.copy()

    st.markdown(f"**{len(display_df)} 件の予約**")

    if display_df.empty:
        st.info("該当する予約はありません。")
    else:
        slot_order = {s: i for i, s in enumerate(TIME_SLOTS)}
        display_df["_slot_order"] = display_df["時間帯"].map(slot_order).fillna(99)
        display_df = (
            display_df
            .sort_values(["日付", "_slot_order"])
            .drop(columns=["_slot_order"])
        )
        st.dataframe(display_df.reset_index(drop=True), use_container_width=True, height=500)

    st.markdown("---")
    st.markdown("**📥 CSVダウンロード**")
    csv_bytes = df_admin.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="📥 reservations.csv をダウンロード",
        data=csv_bytes,
        file_name="reservations.csv",
        mime="text/csv",
    )
