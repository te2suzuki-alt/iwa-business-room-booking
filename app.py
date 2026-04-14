import streamlit as st

st.set_page_config(page_title="テスト", layout="wide")

st.write("### デバッグ情報")
st.write(f"is_logged_in 属性あり: {hasattr(st.user, 'is_logged_in')}")

if not hasattr(st.user, "is_logged_in"):
    st.error("認証設定が未構成です")
    st.stop()

st.write(f"is_logged_in: {st.user.is_logged_in}")

if not st.user.is_logged_in:
    st.title("ログインテスト")
    try:
        st.login()
    except Exception as e:
        st.error(f"エラー: {type(e).__name__}: {e}")
    st.stop()

st.success("ログイン成功！")
st.write(f"名前: {getattr(st.user, 'name', '不明')}")
st.write(f"メール: {getattr(st.user, 'email', '不明')}")
st.write(f"hd: {getattr(st.user, 'hd', '不明')}")

if st.button("ログアウト"):
    st.logout()
