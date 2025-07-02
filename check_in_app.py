import streamlit as st
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd

# ====== Google Sheets 認證區 ======
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
info = dict(st.secrets["google_service_account"])
credentials = Credentials.from_service_account_info(info, scopes=scope)
client = gspread.authorize(credentials)
spreadsheet = client.open("打卡紀錄")
# sheet = spreadsheet.sheet1

# 根據當前月份取得對應的工作表（例如：202507）
now = datetime.utcnow()+ timedelta(hours=8)  # 台灣時間
sheet_name = now.strftime("%Y%m")  # 例如 "202507"


try:
    sheet = spreadsheet.worksheet(sheet_name)
except gspread.exceptions.WorksheetNotFound:
    st.error(f"❌ 找不到工作表：{sheet_name}，請確認該月份工作表是否存在。")
    st.stop()

# ====== Streamlit 頁面設定 ======
st.set_page_config(page_title="線上打卡系統", page_icon="🕘")
st.title("🔐 登入打卡系統")

# ====== 使用者帳密載入 ======
users = st.secrets["users"]

# ====== Session 狀態 ======
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# ====== 登入畫面 ======
if not st.session_state["logged_in"]:
    username = st.text_input("帳號")
    password = st.text_input("密碼", type="password")
    if st.button("登入"):
        if username in users and users[username] == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.success("✅ 登入成功")
            st.rerun()
        else:
            st.error("❌ 帳號或密碼錯誤")
    st.stop()

# ====== 已登入畫面 ======
st.success(f"👋 歡迎回來：{st.session_state['username']}")

# ====== 打卡功能 ======
if st.button("✅ 我要打卡"):
    now = datetime.utcnow() + timedelta(hours=8)  # 台灣時間
    date = now.strftime("%Y/%m/%d")
    time = now.strftime("%H:%M:%S")
    sheet_name = now.strftime("%Y%m")  # 根據打卡時間選擇表單

    try:
        sheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ 找不到工作表：{sheet_name}，請確認該月份工作表是否存在。")
        st.stop()

    sheet.append_row([st.session_state["username"], date, time])
    st.success(f"🎉 打卡成功！時間：{date} {time}")
    st.rerun()

# ====== 歷史紀錄顯示 ======
st.subheader("📜 我的歷史打卡紀錄")

# try:
#     records = sheet.get_all_values()  # [['帳號', '日期', '時間'], ...]
#     if len(records) <= 1:
#         st.info("⚠️ 尚無任何打卡資料。")
#     else:
#         header, *rows = records
#         df = pd.DataFrame(rows, columns=header)
#         user_df = df[df["姓名"] == st.session_state["username"]]
#         if user_df.empty:
#             st.info("❗你尚未打過卡。")
#         else:
#             user_df = user_df.tail(10).reset_index(drop=True)
#             user_df.index += 1  # 顯示從 1 開始
#             st.table(user_df)
# except Exception as e:
#     st.error(f"❌ 無法讀取打卡資料：{e}")
# 顯示本月的紀錄
try:
    records = sheet.get_all_values()
    if len(records) <= 1:
        st.info("⚠️ 本月尚無任何打卡資料。")
    else:
        header, *rows = records
        df = pd.DataFrame(rows, columns=header)
        user_df = df[df["帳號"] == st.session_state["username"]]  # 修正這裡的欄位名
        if user_df.empty:
            st.info("❗你本月尚未打過卡。")
        else:
            user_df = user_df.tail(10).reset_index(drop=True)
            user_df.index += 1
            st.table(user_df)
except Exception as e:
    st.error(f"❌ 無法讀取打卡資料：{e}")