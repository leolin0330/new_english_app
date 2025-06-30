import streamlit as st
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import gspread

# ====== Google Sheets 認證區 ======
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
info = dict(st.secrets["google_service_account"])
credentials = Credentials.from_service_account_info(info, scopes=scope)
client = gspread.authorize(credentials)
spreadsheet = client.open("打卡紀錄")
sheet = spreadsheet.sheet1

# ====== 登入區 ======
st.set_page_config(page_title="線上打卡系統", page_icon="🕘")
st.title("🔐 登入打卡系統")

# 載入帳密
users = st.secrets["users"]

# 建立 session 狀態
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

if not st.session_state["logged_in"]:
    username = st.text_input("帳號")
    password = st.text_input("密碼", type="password")
    if st.button("登入"):
        if username in users and users[username] == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.success("✅ 登入成功")
            st.experimental_rerun()  # 重新整理頁面，立即切換到打卡畫面
        else:
            st.error("❌ 帳號或密碼錯誤")
    st.stop()  # 停止後面顯示
else:
    st.success(f"👋 歡迎回來：{st.session_state['username']}")

# ====== 打卡功能 ======
if st.button("✅ 我要打卡"):
    now = datetime.utcnow() + timedelta(hours=8)  # 台灣時間
    date = now.strftime("%Y/%m/%d")
    time = now.strftime("%H:%M:%S")
    sheet.append_row([st.session_state["username"], date, time])
    st.success(f"🎉 打卡成功！時間：{date} {time}")
