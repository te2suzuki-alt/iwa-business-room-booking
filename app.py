import streamlit as st

st.set_page_config(page_title="テスト", layout="wide")

if not hasattr(st.user, "is_logged_in"):
    st.error("認証設定が未構成です")
    st.stop()

if not st.user.is_logged_in:
    st.title("ログインテスト")
    st.login()
    st.stop()

st.success(f"ログイン成功！")
st.write(f"名前: {getattr(st.user, 'name', '不明')}")
st.write(f"メール: {getattr(st.user, 'email', '不明')}")
st.write(f"hd: {getattr(st.user, 'hd', '不明')}")
st.logout()
