"""
ビジネス講義室予約システム — app.py
動作要件：
  - Streamlit >= 1.42.0
  - .streamlit/secrets.toml に [auth] セクションが正しく設定されていること
  - Google Cloud Console で OAuth 2.0 クライアント ID を取得済みであること
"""

import streamlit as st
import pandas as pd
import os
from datetime import date, datetime, timedelta

# ═════════════════════════════════════════════════════════════════
# 定数
# ═════════════════════════════════════════════════════════════════
CSV_FILE        = "reservations.csv"
ADMIN_PASSWORD  = "admin1234"          # ← 管理者パスワード（適宜変更）
TIME_SLOTS      = ["1限", "2限", "3限", "4限", "5限", "昼休み", "放課後"]
GRADES          = ["1年", "2年", "3年", "4年"]
COLUMNS         = ["日付", "時間帯", "学年", "氏名", "使用目的", "備考", "登録日時"]
WEEKDAY_JP      = ["月", "火", "水", "木", "金", "土", "日"]
ALLOWED_DOMAINS = {"stu.hokkyodai.ac.jp", "i.hokkyodai.ac.jp"}

# ═════════════════════════════════════════════════════════════════
# ページ設定（必ず最初に呼ぶ）
# ═════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="ビジネス講義室予約システム",
    page_icon="🏫",
    layout="wide",
)

# ═════════════════════════════════════════════════════════════════
# ── STEP 0: 認証設定の事前チェック ──
#
# secrets.toml の [auth] が未設定だと st.user に is_logged_in が存在しない。
# AttributeError を防ぐために hasattr で確認し、
# 未設定の場合は具体的なエラー案内を表示して停止する。
# ═════════════════════════════════════════════════════════════════

def _show_auth_config_error() -> None:
    """認証未設定時に詳細な設定案内を表示する"""
    st.error("⚙️ 認証設定が見つかりません")
    st.markdown("""
### 解決方法

アプリのフォルダに `.streamlit/secrets.toml` を作成し、以下の内容を記入してください。

```toml
# .streamlit/secrets.toml  ※ [auth] にすべてフラットに書く（[auth.google] は使わない）

[auth]
redirect_uri        = "https://iwa-business-room-booking.streamlit.app/oauth2callback"
cookie_secret       = "ランダム文字列"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
client_id           = "YOUR_CLIENT_ID.apps.googleusercontent.com"
client_secret       = "YOUR_CLIENT_SECRET"
```

#### 設定手順

1. **Google Cloud Console** で OAuth 2.0 クライアント ID を取得する  
   https://console.cloud.google.com/ → 「APIとサービス」→「認証情報」→「OAuth 2.0 クライアントID」作成  
   種別：**ウェブ アプリケーション**

2. **承認済みリダイレクト URI** に以下を追加する  
   `http://localhost:8501/oauth2callback`

3. 取得した `client_id` と `client_secret` を `secrets.toml` に記入する

4. `cookie_secret` は Python で以下を実行して得た値を貼り付ける  
   ```python
   import secrets
   print(secrets.token_hex(32))
   ```

5. Streamlit を再起動する（`Ctrl+C` → `streamlit run app.py`）

#### Streamlit バージョンの確認

`st.user.is_logged_in` は **Streamlit 1.42.0 以上** が必要です。  
バージョン確認：`streamlit --version`  
アップグレード：`pip install --upgrade streamlit`
""")


# hasattr で安全に確認（secrets.toml 未設定時は is_logged_in が存在しない）
if not hasattr(st.user, "is_logged_in"):
    _show_auth_config_error()
    st.stop()

# ═════════════════════════════════════════════════════════════════
# ── STEP 1: 未ログイン時 → ログイン画面を表示して停止 ──
# ═════════════════════════════════════════════════════════════════

if not st.user.is_logged_in:
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }
.login-wrap {
    display: flex; justify-content: center; margin-top: 80px;
}
.login-box {
    width: 100%; max-width: 440px;
    padding: 44px 40px;
    border-radius: 18px;
    background: #ffffff;
    box-shadow: 0 4px 32px rgba(0,0,0,0.10);
    text-align: center;
}
.login-icon  { font-size: 3rem; margin-bottom: 10px; }
.login-title { font-size: 1.55rem; font-weight: 700; color: #1a3a5c; margin-bottom: 6px; }
.login-sub   { font-size: 0.88rem; color: #6b7280; margin-bottom: 32px; line-height: 1.6; }
.login-note  { font-size: 0.78rem; color: #9ca3af; margin-top: 20px; }
</style>
<div class="login-wrap">
  <div class="login-box">
    <div class="login-icon">🏫</div>
    <div class="login-title">ビジネス講義室予約システム</div>
    <div class="login-sub">
      北海道教育大学の Google アカウント<br>
      （stu.hokkyodai.ac.jp または i.hokkyodai.ac.jp）<br>
      でログインしてください
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # st.login() はフォーム外・Streamlit ウィジェットとして配置する必要がある
    col_l, col_c, col_r = st.columns([1, 1, 1])
    with col_c:
        try:
            st.login()
        except Exception as e:
            st.error(f"ログインエラー：{e}")
            st.stop()

    st.stop()   # ここより下は未ログイン時に実行しない

# ═════════════════════════════════════════════════════════════════
# ── STEP 2: ログイン済み → hd claim によるドメイン検証 ──
#
# st.user から取得できる主な属性（Google OIDC）:
#   is_logged_in : bool
#   email        : メールアドレス（偽装リスクあり → 判定には使わない）
#   name         : 表示名
#   hd           : Google Hosted Domain（大学 Workspace アカウントのみ付与）
#   picture      : プロフィール画像 URL
#   sub          : Google 内部ユーザー ID
#
# ※ hd は Google が署名した ID トークン内のクレームであり、
#   ユーザーが偽装することはできない。email 末尾の文字列一致より安全。
# ═════════════════════════════════════════════════════════════════

user_hd    = getattr(st.user, "hd",    None)
user_email = getattr(st.user, "email", "")
user_name  = getattr(st.user, "name",  user_email)

if user_hd not in ALLOWED_DOMAINS:
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }
</style>
""", unsafe_allow_html=True)
    st.error("🚫 このアプリは北海道教育大学の Google アカウントのみ利用できます。")

    with st.container(border=True):
        st.markdown("**ログイン中のアカウント情報**")
        st.markdown(f"- メールアドレス：`{user_email}`")
        st.markdown(f"- ドメイン（hd）：`{user_hd}`")
        st.markdown("")
        st.markdown("利用できるドメイン：`stu.hokkyodai.ac.jp` / `i.hokkyodai.ac.jp`")

    if st.button("🔄 別のアカウントでログインし直す", type="primary"):
        st.logout()

    st.stop()   # 許可外ドメインはここで停止

# ─── ここより下は許可済みユーザーのみ到達 ───────────────────────

# ═════════════════════════════════════════════════════════════════
# session_state の初期化
# ═════════════════════════════════════════════════════════════════
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False
if "flash_message" not in st.session_state:
    st.session_state["flash_message"] = None

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
    """指定日の {時間帯: 予約行(Series)} を返す"""
    day_df = df[df["日付"] == target_date]
    return {row["時間帯"]: row for _, row in day_df.iterrows()}

def is_slot_taken(target_date: str, slot: str) -> bool:
    """送信直前に最新CSVを再読み込みして重複を二重チェックする"""
    latest_df = load_csv()
    return not latest_df[
        (latest_df["日付"] == target_date) & (latest_df["時間帯"] == slot)
    ].empty

def check_admin() -> bool:
    """管理者パスワード認証済みかを返す"""
    return st.session_state.get("is_admin", False)

def build_calendar_html(df: pd.DataFrame, today: date) -> str:
    """当日を含む7日分のカレンダーHTMLテーブルを生成して返す"""
    days = [today + timedelta(days=i) for i in range(7)]

    # 全予約を {(日付文字列, 時間帯): row} に変換
    reservation_map: dict = {}
    for _, row in df.iterrows():
        reservation_map[(row["日付"], row["時間帯"])] = row

    # ── ヘッダー行 ──
    header_cells = '<th class="cal-th cal-corner">時間帯</th>'
    for d in days:
        d_str      = d.strftime("%Y-%m-%d")
        m_d        = f"{d.month}/{d.day}"     # Windows互換（%-m/%-d は非対応）
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

    # ── データ行 ──
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
# グローバルスタイル
# ═════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }

/* ─── ヘッダー ─── */
.main-title {
    font-size: 2rem; font-weight: 700; color: #1a3a5c;
    border-bottom: 3px solid #2e7bcf;
    padding-bottom: 0.3rem; margin-bottom: 0.2rem;
}
.sub-title { color: #6b7280; font-size: 0.95rem; margin-bottom: 0.8rem; }

/* ─── ログインユーザー情報バー ─── */
.user-bar {
    background: #f0f7ff; border: 1px solid #bfdbfe;
    border-radius: 8px; padding: 8px 16px;
    font-size: 0.88rem; color: #1e40af;
    margin-bottom: 12px;
}

/* ─── 予約状況カード ─── */
.slot-card {
    border-radius: 10px; padding: 14px 18px; margin-bottom: 10px;
    font-size: 0.93rem; border-left: 5px solid; line-height: 1.7;
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
    overflow-x: auto; margin-top: 8px;
    border-radius: 10px; box-shadow: 0 2px 12px rgba(0,0,0,0.08);
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
# サイドバー
# ═════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🏫 メニュー")
    page = st.radio(
        "画面を選択",
        ["📅 予約・閲覧", "🔧 管理者画面"],
        label_visibility="collapsed",
    )

    # ── Google アカウント情報 & ログアウト ──
    st.markdown("---")
    st.markdown("### 👤 ログイン中")
    st.markdown(f"**{user_name}**")
    st.caption(user_email)
    if st.button("🚪 ログアウト", use_container_width=True):
        st.logout()

    # ── 管理者パスワード認証 ──
    st.markdown("---")
    st.markdown("### 🔑 管理者ログイン")
    if not check_admin():
        pwd_input = st.text_input("パスワード", type="password", key="pwd_input")
        if st.button("ログイン", key="admin_login_btn"):
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

    # ── 開発用：st.user デバッグ表示（管理者のみ） ──
    if check_admin():
        st.markdown("---")
        with st.expander("🛠️ [開発用] st.user の内容", expanded=False):
            try:
                st.json({
                    "is_logged_in": getattr(st.user, "is_logged_in", None),
                    "email":        getattr(st.user, "email",        None),
                    "name":         getattr(st.user, "name",         None),
                    "hd":           getattr(st.user, "hd",           None),
                    "picture":      getattr(st.user, "picture",      None),
                    "sub":          getattr(st.user, "sub",          None),
                })
            except Exception as e:
                st.warning(f"st.user 取得エラー: {e}")

# ═════════════════════════════════════════════════════════════════
# メインエリア：タイトル & ユーザーバー
# ═════════════════════════════════════════════════════════════════
st.markdown('<div class="main-title">🏫 ビジネス講義室予約システム</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">ビジネス講義室 ／ 予約は当日を含む7日先まで可能</div>', unsafe_allow_html=True)

st.markdown(
    f'<div class="user-bar">'
    f'👤 <b>{user_name}</b>&emsp;{user_email}'
    f'&emsp;｜&emsp;ドメイン: <b>{user_hd}</b>'
    f'</div>',
    unsafe_allow_html=True,
)

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
                        # 送信直前に最新CSVで重複を二重チェック
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
