import streamlit as st
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd

# --- Google Sheets 認證 ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
info = dict(st.secrets["google_service_account"])
credentials = Credentials.from_service_account_info(info, scopes=scope)
client = gspread.authorize(credentials)
spreadsheet = client.open("打卡紀錄")

# --- 輔助函式：根據時間抓對月份的 sheet ---
def get_sheet_for(dt):
    sheet_name = dt.strftime("%Y%m")
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"❌ 找不到對應月份的工作表：{sheet_name}")
        st.stop()

# --- Streamlit 設定 ---
st.set_page_config(page_title="線上打卡系統", page_icon="🕘")
st.title("🔐 登入打卡系統(測試區)")
users = st.secrets["users"]

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# --- 登入流程 ---
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

st.success(f"👋 歡迎回來：{st.session_state['username']}")

# --- 打卡功能 ---
if st.button("✅ 我要打卡"):
    now = datetime.utcnow() + timedelta(hours=8)
    date = now.strftime("%Y/%m/%d")
    time = now.strftime("%H:%M:%S")
    sheet = get_sheet_for(now)
    sheet.append_row([st.session_state["username"], date, time])
    st.success(f"🎉 打卡成功！時間：{date} {time}")
    st.rerun()

# --- 顯示歷史打卡紀錄（可選月份） ---
st.subheader("📜 我的歷史打卡紀錄（可選月份）")

# 選單：顯示可用的月份頁籤（從 Google Sheets 抓取所有工作表名稱）
available_sheets = [ws.title for ws in spreadsheet.worksheets() if ws.title.isdigit()]
available_sheets.sort(reverse=True)  # 最近的在最上面

selected_month = st.selectbox("請選擇要查看的月份：", available_sheets)

try:
    sheet = spreadsheet.worksheet(selected_month)
    records = sheet.get_all_values()

    if len(records) <= 1:
        st.info("⚠️ 選擇的月份尚無任何打卡資料。")
    else:
        header, *rows = records
        df = pd.DataFrame(rows, columns=header)

        if "帳號" in df.columns:
            user_df = df[df["帳號"] == st.session_state["username"]]
        elif "姓名" in df.columns:
            user_df = df[df["姓名"] == st.session_state["username"]]
        else:
            st.warning("⚠️ 此表單缺少正確的使用者欄位（帳號或姓名）")
            st.stop()

        if user_df.empty:
            st.info("❗你在這個月份尚未打過卡。")
        else:
            # 日期 + 時間合併成 datetime 並排序
            user_df["打卡時間"] = pd.to_datetime(user_df["日期"] + " " + user_df["時間"], format="%Y/%m/%d %H:%M:%S")
            user_df = user_df.sort_values(by="打卡時間", ascending=True)
            user_df = user_df.head(10).reset_index(drop=True)
            user_df.index += 1

            st.table(user_df.drop(columns=["打卡時間"]))
except Exception as e:
    st.error(f"❌ 無法讀取打卡資料：{e}")

