import streamlit as st
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import io
from google.cloud import secretmanager
import json
import requests
from admin_user_management import add_user, view_all_users, manage_user_status,manage_accounts



# --- 語言與登入狀態初始化 ---
if "language" not in st.session_state:
    st.session_state["language"] = "中文"
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "role" not in st.session_state:
    st.session_state["role"] = "user"

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

# --- 讀取多語言文字 ---
@st.cache_resource
def load_translation_json(url: str):
    response = requests.get(url)
    return response.json()

lang = load_translation_json("https://raw.githubusercontent.com/leolin0330/new_english_app/main/lang_config.json")
text = lang[st.session_state["language"]]

# --- 使用者資料快取 ---
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
        st.error(f"❌ {text.get('read_error', '無法讀取使用者資料表')}：{e}")
        return {}

is_admin = st.session_state.get("role", "user") == "admin"
title_key = "title_admin" if is_admin else "title_user"
st.set_page_config(page_title=text[title_key], page_icon="🕘")

# --- 語言切換按鈕 ---
col1, col3 = st.columns([11, 1])
with col3:
    toggle_lang = "English" if st.session_state["language"] == "中文" else "中文"
    if st.button(toggle_lang):
        st.session_state["language"] = toggle_lang
        st.rerun()

st.title(text[title_key])

users = get_users_from_sheet()

# --- 登入流程 ---
if not st.session_state["logged_in"]:
    username = st.text_input(text["username"])
    password = st.text_input(text["password"], type="password")
    if st.button(text["login"]):
        if username not in users:
            st.error(text["login_error"])  # 你這份翻譯中沒有細分錯誤，統一用 login_error
        else:
            user_info = users[username]
            if not user_info["enabled"]:
                st.error(text.get("account_disabled", "⚠️ 該帳號已停用"))
            elif user_info["password"] != password:
                st.error(text["login_error"])
            else:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.session_state["role"] = user_info.get("role", "user")
                st.toast(text["login_success"], icon="✅")
                st.rerun()
    st.stop()

# --- 登出按鈕 ---
logout_label = "🚪 登出" if st.session_state["language"] == "中文" else "🚪 Logout"
if st.button(logout_label):
    st.session_state.clear()
    st.rerun()

# ✅ 主畫面顯示
st.success(f"{text['welcome']}{st.session_state['username']}")
st.divider()
st.markdown("### 👇 功能選單")


# --- 管理者功能選單（支援語言切換並保持選擇不變）---
# 選單區
if is_admin:
    menu_keys = text["admin_menu_keys"]
    current_lang = st.session_state["language"]

    if "admin_option_key" not in st.session_state:
        st.session_state["admin_option_key"] = menu_keys[0]

    with st.sidebar:
        st.header("🛠️ 管理功能")

        if current_lang == "中文":
            options = [text["admin_menu_options"][k].strip() for k in menu_keys]
        else:
            options = [lang["English"]["admin_menu_options_en"][k].strip() for k in menu_keys]

        current_key = st.session_state["admin_option_key"]
        default_index = menu_keys.index(current_key) if current_key in menu_keys else 0

        selected_label = st.radio("請選擇功能：", options, index=default_index)
        selected_key = menu_keys[options.index(selected_label)]

        if selected_key != current_key:
            st.session_state["admin_option_key"] = selected_key
            st.rerun()




# --- 呼叫管理功能 ---
admin_option_key = st.session_state.get("admin_option_key", "")

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

# --- 查看打卡紀錄（重構版） ---
def show_checkin_records():
    st.subheader(text["history_title"])

    @st.cache_data(ttl=60)
    def get_all_worksheets(_spreadsheet):
        return [ws.title for ws in _spreadsheet.worksheets() if ws.title.isdigit()]

    available_sheets = get_all_worksheets(spreadsheet)
    available_sheets.sort()

    if not available_sheets:
        st.warning("⚠️ 尚無任何打卡工作表")
        st.info("請先有人打卡，或由管理員新增一筆測試資料")
        return

    current_month = datetime.utcnow() + timedelta(hours=8)
    current_sheet = current_month.strftime("%Y%m")
    default_index = available_sheets.index(current_sheet) if current_sheet in available_sheets else 0

    selected_month = st.selectbox(text["select_month"], available_sheets, index=default_index)

    try:
        sheet = spreadsheet.worksheet(selected_month)
        records = sheet.get_all_values()

        if len(records) <= 1:
            st.info("⚠️ 這個月份尚無任何打卡資料")
            return

        header, *rows = records
        df = pd.DataFrame(rows, columns=header)

        # 判斷帳號欄位
        if "帳號" in df.columns:
            key_col = "帳號"
        elif "姓名" in df.columns:
            key_col = "姓名"
        else:
            st.warning(text["missing_column"])
            return

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
            return

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

        # 管理員可下載 Excel
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

# --- 一般使用者打卡按鈕 ---
if not is_admin:
    if st.button(text["checkin"]):
        check_in()

# --- 管理功能選單 ---
if admin_option_key == "view_records":
    show_checkin_records()
elif admin_option_key == "manage_accounts":
    manage_accounts(client, text)

# --- 如果是一般使用者，顯示紀錄 ---
if not is_admin:
    show_checkin_records()

