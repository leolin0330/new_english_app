import streamlit as st
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import io
from google.cloud import secretmanager
import json

# --- 快取 Secret ---
@st.cache_resource
def get_cached_secret(secret_id: str, version: str = "latest") -> dict:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/616566246123/secrets/{secret_id}/versions/{version}"
    response = client.access_secret_version(request={"name": name})
    payload = response.payload.data.decode("UTF-8")
    return json.loads(payload)

# --- 快取 Google Sheets 認證 ---
@st.cache_resource
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    info = get_cached_secret("google_service_account")
    credentials = Credentials.from_service_account_info(info, scopes=scope)
    return gspread.authorize(credentials)

client = get_gspread_client()
spreadsheet = client.open("打卡紀錄")

# --- 使用者資訊快取 ---
@st.cache_data(ttl=30)
def get_users_from_sheet():
    try:
        user_sheet = client.open("users_login").sheet1
        records = user_sheet.get_all_records()
        users_dict = {}
        for row in records:
            enabled = str(row.get("是否啟用", "Y")).strip().upper() == "Y"
            users_dict[row["帳號"]] = {
                "password": row["密碼"],
                "role": row.get("角色", "user"),
                "enabled": enabled
            }
        return users_dict
    except Exception as e:
        st.error(f"❌ 無法讀取使用者資料表：{e}")
        return {}

users = get_users_from_sheet()

# --- 語言與登入狀態初始化 ---
if "language" not in st.session_state:
    st.session_state["language"] = "中文"
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# --- 語言切換按鈕 ---
col1, col3 = st.columns([11, 1])
with col3:
    toggle_lang = "English" if st.session_state["language"] == "中文" else "中文"
    if st.button(toggle_lang):
        st.session_state["language"] = toggle_lang

# --- 語系文字 ---
is_admin = st.session_state.get("role") == "admin"


text = {
    "中文": {
        "title": "🔐 管理者介面（打卡系統測試區)）" if is_admin else "🔐 登入打卡系統(GCP測試區)",
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
        "title": "🔐 Admin Panel (GCP Clock-in System)" if is_admin else "🔐 Sign-in System (GCP Test Area)",
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

# --- 頁面設定 ---
st.set_page_config(page_title=text["title"], page_icon="🕘")
st.title(text["title"])

# --- 登入流程 ---
if not st.session_state["logged_in"]:
    username = st.text_input(text["username"])
    password = st.text_input(text["password"], type="password")
    if st.button(text["login"]):
        if username not in users:
            st.error(text["login_error"])
        else:
            user_info = users[username]
            if not user_info["enabled"]:
                st.error("⚠️ 該帳號已停用")
            elif user_info["password"] == password:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.session_state["role"] = user_info.get("role", "user")
                st.success(text["login_success"])
                st.rerun()
            else:
                st.error(text["login_error"])
    st.stop()

# --- 登出按鈕 ---
# --- 登出按鈕 ---
if st.button("🚪 登出" if st.session_state["language"] == "中文" else "🚪 Logout"):
    st.session_state.clear()
    st.rerun()

st.success(f"{text['welcome']}{st.session_state['username']}")

# --- 管理者功能側邊欄 ---
if is_admin:
    with st.sidebar:
        st.header("🛠️ 管理功能")
        admin_option = st.radio("請選擇功能：", ["📊 查看打卡紀錄", "➕ 新增帳號"])
else:
    admin_option = None

# --- 自動建立當月工作表 ---
def get_sheet_for(dt):
    sheet_name = dt.strftime("%Y%m")
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
        worksheet.append_row(["姓名", "日期", "時間"])
        return worksheet

# --- 打卡功能 ---
def check_in():
    now = datetime.utcnow() + timedelta(hours=8)
    date = now.strftime("%Y/%m/%d")
    time = now.strftime("%H:%M:%S")
    sheet = get_sheet_for(now)
    sheet.append_row([st.session_state["username"], date, time])
    st.success(f"{text['checkin_success']}{date} {time}")
    st.rerun()

# --- 一般使用者打卡按鈕 ---
if not is_admin:
    if st.button(text["checkin"]):
        check_in()

# --- 管理者新增帳號 ---
if is_admin and admin_option == "➕ 新增帳號":
    st.subheader("👤 管理者 - 新增使用者帳號")
    with st.form("add_user_form", clear_on_submit=True):
        new_username = st.text_input("👤 新帳號")
        new_password = st.text_input("🔑 密碼", type="password")
        new_role = st.selectbox("🧑‍💼 角色", options=["user", "admin"])
        enabled = st.checkbox("✅ 啟用帳號", value=True)

        submitted = st.form_submit_button("➕ 新增帳號")
        if submitted:
            try:
                user_sheet = client.open("users_login").sheet1
                existing_users = [row["帳號"] for row in user_sheet.get_all_records()]
                if new_username in existing_users:
                    st.warning("⚠️ 此帳號已存在，請使用其他帳號")
                elif not new_username or not new_password:
                    st.warning("⚠️ 請輸入完整帳號與密碼")
                else:
                    user_sheet.append_row([new_username, new_password, new_role, "Y" if enabled else "N"])
                    st.success(f"✅ 已新增帳號：{new_username}（角色：{new_role}）")
                    st.cache_data.clear()
            except Exception as e:
                st.error(f"❌ 新增帳號失敗：{e}")

# --- 歷史紀錄區塊 ---
if not is_admin or admin_option == "📊 查看打卡紀錄":
    st.subheader(text["history_title"])

    @st.cache_data(ttl=60)
    def get_all_worksheets(_spreadsheet):
        return [ws.title for ws in spreadsheet.worksheets() if ws.title.isdigit()]

    available_sheets = get_all_worksheets(spreadsheet)
    available_sheets.sort()

    current_month = datetime.utcnow() + timedelta(hours=8)
    current_sheet = current_month.strftime("%Y%m")
    default_index = available_sheets.index(current_sheet) if current_sheet in available_sheets else 0

    if not available_sheets:
        st.warning("⚠️ 尚無任何打卡工作表")
        st.stop()

    selected_month = st.selectbox(text["select_month"], available_sheets, index=default_index)

    try:
        sheet = spreadsheet.worksheet(selected_month)
        records = sheet.get_all_values()

        if len(records) <= 1:
            st.info(text["no_data"])
            st.stop()

        header, *rows = records
        df = pd.DataFrame(rows, columns=header)

        if "帳號" in df.columns:
            key_col = "帳號"
        elif "姓名" in df.columns:
            key_col = "姓名"
        else:
            st.warning(text["missing_column"])
            st.stop()

        if is_admin:
            user_list = sorted(df[key_col].unique())
            user_list.insert(0, text["all_users_label"])
            selected_user = st.selectbox(text["select_user"], user_list)
            if selected_user != text["all_users_label"]:
                df = df[df[key_col] == selected_user]
        else:
            df = df[df[key_col] == st.session_state["username"]]

        if df.empty:
            st.info(text["no_record"] if not is_admin else text["no_data"])
            st.stop()

        if "日期" not in df.columns or "時間" not in df.columns:
            st.warning("⚠️ 表單缺少『日期』或『時間』欄位，無法顯示打卡時間排序")
        else:
            try:
                df["打卡時間"] = pd.to_datetime(df["日期"] + " " + df["時間"], format="%Y/%m/%d %H:%M:%S", errors='coerce')
                df = df.dropna(subset=["打卡時間"])
                df = df.sort_values("打卡時間").head(100).reset_index(drop=True)
                df.index += 1
            except Exception as e:
                st.error(f"❌ 時間欄位處理錯誤：{e}")

        column_map = text["columns"]
        df_display = df.drop(columns=["打卡時間"]).rename(columns=column_map)
        st.table(df_display)

        if is_admin:
            excel_buffer = io.BytesIO()
            df_display.to_excel(excel_buffer, index=False, sheet_name=selected_month)
            excel_buffer.seek(0)
            user_label = selected_user if selected_user != text["all_users_label"] else text["all_users_label"]
            filename = f"{selected_month}_{user_label}_{text['file_label']}.xlsx"

            st.download_button(
                label="📥 " + text["download"],
                data=excel_buffer,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except gspread.exceptions.WorksheetNotFound:
        st.error(f"{text['sheet_not_found']}{selected_month}")
    except Exception as e:
        st.error(f"{text['read_error']}{e}")
