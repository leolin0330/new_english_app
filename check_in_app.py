import streamlit as st
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import io
import json
from google.cloud import secretmanager

# --- 語言切換按鈕（模擬右上角） ---
if "language" not in st.session_state:
    st.session_state["language"] = "中文"
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# 調整：右邊靠邊顯示按鈕（只留一個切換按鈕）
col1, col3 = st.columns([11, 1])
with col3:
    toggle_lang = "English" if st.session_state["language"] == "中文" else "中文"
    if st.button(toggle_lang):
        st.session_state["language"] = toggle_lang
        # st.rerun()

# --- 語系文字 ---
is_admin = st.session_state["username"] == "admin"

text = {
    "中文": {
        "title": "🔐 管理者介面（打卡系統正是區）" if is_admin else "🔐 登入打卡系統(GCP正試區)",
        "select_user": "👥 選擇人員",
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
        "read_error": "❌ 無法讀取打卡資料：",
        "download": "📥 下載 Excel",
        "columns": {
            "姓名": "姓名",
            "日期": "日期",
            "時間": "時間"
        },
        "all_users_label": "所有人",
        "file_label": "打卡紀錄"
    },
    "English": {
        "title": "🔐 Admin Panel (GCP Clock-in System)" if is_admin else "🔐 Sign-in System(GCP Test Area)",
        "select_user": "👥 Select User",
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
        "read_error": "❌ Failed to read check-in data: ",
        "download":"📥 Download Excel",
        "columns": {
            "姓名": "Name",
            "日期": "Date",
            "時間": "Time"
        },
        "all_users_label": "All",
        "file_label": "Check-in Record"
    }
}[st.session_state["language"]]

# --- Streamlit 頁面設定 ---
st.set_page_config(page_title=text["title"], page_icon="🕘")
st.title(text["title"])

# 從 GCP Secret Manager 取得金鑰
def get_secret(secret_id: str, version: str = "latest") -> dict:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/616566246123/secrets/{secret_id}/versions/{version}"
    response = client.access_secret_version(request={"name": name})
    payload = response.payload.data.decode("UTF-8")
    return json.loads(payload)


# --- Google Sheets 認證 ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
info = get_secret("google_service_account")  # 改用 GCP Secret Manager
credentials = Credentials.from_service_account_info(info, scopes=scope)
client = gspread.authorize(credentials)
spreadsheet = client.open("打卡紀錄")

# --- 使用者資訊 ---
users = get_secret("users")  # 改用 Secret Manager 讀 users JSON


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

# 判斷是否為管理者
is_admin = st.session_state["username"] == "admin"

# --- 打卡按鈕 ---
if not is_admin:
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
default_index = available_sheets.index(current_sheet) if current_sheet in available_sheets else -1
if default_index == -1:
    st.warning("⚠️ 尚無任何打卡工作表")
    st.stop()

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
            key_col = "帳號"
        elif "姓名" in df.columns:
            key_col = "姓名"
        else:
            st.warning(text["missing_column"])
            st.stop()

        # 管理員選擇要查看的人員
        if is_admin:
            user_list = sorted(df[key_col].unique())
            user_list.insert(0, text["all_users_label"])
            selected_user = st.selectbox(text["select_user"], user_list)
            if selected_user != text["all_users_label"]:
                df = df[df[key_col] == selected_user]
        else:
            df = df[df[key_col] == st.session_state["username"]]

        # ✅ 改成：先判斷有資料再進行時間轉換
        if df.empty:
            st.info(text["no_record"] if not is_admin else text["no_data"])
        else:
            # ✅ 時間轉換只對篩選後的資料進行
            df["打卡時間"] = pd.to_datetime(df["日期"] + " " + df["時間"], format="%Y/%m/%d %H:%M:%S")
            df = df.sort_values(by="打卡時間", ascending=True)
            df = df.head(100).reset_index(drop=True)
            df.index += 1

            # 根據語言轉換欄位名稱
            column_map = text["columns"]
            df_renamed = df.drop(columns=["打卡時間"]).rename(columns=column_map)

            st.table(df_renamed)

            if is_admin:
                excel_buffer = io.BytesIO()
                export_df = df.drop(columns=["打卡時間"]).rename(columns=column_map)
                export_df.to_excel(excel_buffer, index=False, sheet_name=selected_month)
                excel_buffer.seek(0)

                user_label = selected_user if selected_user != text["all_users_label"] else text["all_users_label"]
                filename = f"{selected_month}_{user_label}_{text['file_label']}.xlsx"

                st.download_button(
                    label="📥 " + ("下載 Excel" if st.session_state["language"] == "中文" else "Download Excel"),
                    data=excel_buffer,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

except gspread.exceptions.WorksheetNotFound:
    st.error(f"{text['sheet_not_found']}{selected_month}")
except Exception as e:
    st.error(f"{text['read_error']}{e}")



