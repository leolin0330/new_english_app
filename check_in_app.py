import streamlit as st
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd

# --- 語言切換按鈕（模擬右上角） ---
if "language" not in st.session_state:
    st.session_state["language"] = "中文"

# 調整：右邊靠邊顯示按鈕
col1, col2, col3 = st.columns([10, 1, 1])
with col3:
    if st.session_state["language"] != "中文":
        if st.button("中文"):
            st.session_state["language"] = "中文"
            st.rerun()
with col2:
    if st.session_state["language"] != "English":
        if st.button("English"):
            st.session_state["language"] = "English"
            st.rerun()

# --- 語系文字 ---
text = {
    "中文": {
        "title": "🔐 登入打卡系統(測試區)",
        "username": "帳號",
        "password": "密碼",
        "login": "登入",
        "login_success": "✅ 登入成功",
        "login_error": "❌ 帳號或密碼錯誤",
        "welcome": "👋 歡迎回來：",
        "checkin": "✅ 我要打卡",
        "checkin_success": "🎉 打卡成功！時間：",
        "history_title": "📜 我的歷史打卡紀錄（可選月份）",
        "select_month": "請選擇要查看的月份：",
        "no_data": "⚠️ 選擇的月份尚無任何打卡資料。",
        "no_record": "❗你在這個月份尚未打過卡。",
        "missing_column": "⚠️ 此表單缺少正確的使用者欄位（帳號或姓名）",
        "sheet_not_found": "❌ 找不到對應月份的工作表：",
        "read_error": "❌ 無法讀取打卡資料："
    },
    "English": {
        "title": "🔐 Sign-in System (Test Area)",
        "username": "Username",
        "password": "Password",
        "login": "Login",
        "login_success": "✅ Login successful",
        "login_error": "❌ Incorrect username or password",
        "welcome": "👋 Welcome back: ",
        "checkin": "✅ Clock In",
        "checkin_success": "🎉 Clock-in success! Time: ",
        "history_title": "📜 My Check-in History (selectable month)",
        "select_month": "Please select a month:",
        "no_data": "⚠️ No check-in data for this month.",
        "no_record": "❗You have not checked in this month.",
        "missing_column": "⚠️ Missing 'username' or 'name' column in the sheet",
        "sheet_not_found": "❌ Worksheet not found for: ",
        "read_error": "❌ Failed to read check-in data: "
    }
}[st.session_state["language"]]

# --- Streamlit 頁面設定 ---
st.set_page_config(page_title=text["title"], page_icon="🕘")
st.title(text["title"])

# --- Google Sheets 認證 ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
info = dict(st.secrets["google_service_account"])
credentials = Credentials.from_service_account_info(info, scopes=scope)
client = gspread.authorize(credentials)
spreadsheet = client.open("打卡紀錄")

# --- 使用者資訊 ---
users = st.secrets["users"]

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# --- 登入流程 ---
if not st.session_state["logged_in"]:
    username = st.text_input(text["username"])
    password = st.text_input(text["password"], type="password")
    if st.button(text["login"]):
        if username in users and users[username] == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.success(text["login_success"])
            st.rerun()
        else:
            st.error(text["login_error"])
    st.stop()

st.success(f"{text['welcome']}{st.session_state['username']}")

# --- 自動建立當月工作表 ---
def get_sheet_for(dt):
    sheet_name = dt.strftime("%Y%m")
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
        worksheet.append_row(["姓名", "日期", "時間"])
        return worksheet

# --- 打卡按鈕 ---
if st.button(text["checkin"]):
    now = datetime.utcnow() + timedelta(hours=8)
    date = now.strftime("%Y/%m/%d")
    time = now.strftime("%H:%M:%S")
    sheet = get_sheet_for(now)
    sheet.append_row([st.session_state["username"], date, time])
    st.success(f"{text['checkin_success']}{date} {time}")
    st.rerun()

# --- 顯示歷史紀錄 ---
st.subheader(text["history_title"])

available_sheets = [ws.title for ws in spreadsheet.worksheets() if ws.title.isdigit()]
available_sheets.sort()

current_month = datetime.utcnow() + timedelta(hours=8)
current_sheet = current_month.strftime("%Y%m")
default_index = available_sheets.index(current_sheet) if current_sheet in available_sheets else 0

selected_month = st.selectbox(text["select_month"], available_sheets, index=default_index)

try:
    sheet = spreadsheet.worksheet(selected_month)
    records = sheet.get_all_values()

    if len(records) <= 1:
        st.info(text["no_data"])
    else:
        header, *rows = records
        df = pd.DataFrame(rows, columns=header)

        if "帳號" in df.columns:
            user_df = df[df["帳號"] == st.session_state["username"]]
        elif "姓名" in df.columns:
            user_df = df[df["姓名"] == st.session_state["username"]]
        else:
            st.warning(text["missing_column"])
            st.stop()

        if user_df.empty:
            st.info(text["no_record"])
        else:
            user_df["打卡時間"] = pd.to_datetime(user_df["日期"] + " " + user_df["時間"], format="%Y/%m/%d %H:%M:%S")
            user_df = user_df.sort_values(by="打卡時間", ascending=True)
            user_df = user_df.head(10).reset_index(drop=True)
            user_df.index += 1
            st.table(user_df.drop(columns=["打卡時間"]))
except gspread.exceptions.WorksheetNotFound:
    st.error(f"{text['sheet_not_found']}{selected_month}")
except Exception as e:
    st.error(f"{text['read_error']}{e}")
