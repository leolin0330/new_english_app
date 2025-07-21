import streamlit as st
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import hashlib
import json
import io
import os
import requests
from admin_user_management import add_user, view_all_users, manage_user_status

# --- 語言與登入狀態初始化 ---
if "language" not in st.session_state:
    st.session_state["language"] = "中文"
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "role" not in st.session_state:
    st.session_state["role"] = "user"

# --- Google Sheets 認證 ---
@st.cache_resource
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    info = json.loads(st.secrets["google_service_account"])
    credentials = Credentials.from_service_account_info(info, scopes=scope)
    return gspread.authorize(credentials)

client = get_gspread_client()
spreadsheet = client.open("打卡紀錄")

# --- 載入語系檔 ---
lang_path = os.path.join(os.path.dirname(__file__), "lang_config.json")
with open(lang_path, "r", encoding="utf-8") as f:
    lang_data = json.load(f)

text = lang_data[st.session_state["language"]]

# --- 語言切換按鈕 ---
col1, col3 = st.columns([11, 1])
with col3:
    toggle_lang = "English" if st.session_state["language"] == "中文" else "中文"
    if st.button(toggle_lang):
        st.session_state["language"] = toggle_lang
        st.rerun()

# --- 使用者資料載入 ---
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

users = get_users_from_sheet()
is_admin = st.session_state.get("role", "user") == "admin"
title_key = "title_admin" if is_admin else "title_user"
st.set_page_config(page_title=text[title_key], page_icon="🕘")
st.title(text[title_key])

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
                st.error(text.get("account_disabled", "⚠️ 該帳號已停用"))
            else:
                input_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
                if input_hash == user_info["password"]:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.session_state["role"] = user_info.get("role", "user")
                    st.toast(text["login_success"], icon="✅")
                    st.rerun()
                else:
                    st.error(text["login_error"])
    st.stop()

# --- 登出 ---
if st.button("🚪 登出" if st.session_state["language"] == "中文" else "🚪 Logout"):
    st.session_state.clear()
    st.rerun()

st.success(f"{text['welcome']}{st.session_state['username']}")

# --- 建立當月打卡工作表 ---
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

# --- 查看打卡紀錄 ---
def show_checkin_records():
    st.subheader(text["history_title"])
    sheets = [ws.title for ws in spreadsheet.worksheets() if ws.title.isdigit()]
    sheets.sort()
    if not sheets:
        st.warning(text["no_data"])
        return
    current_month = datetime.utcnow() + timedelta(hours=8).strftime("%Y%m")
    selected_month = st.selectbox(text["select_month"], sheets, index=sheets.index(current_month) if current_month in sheets else 0)

    try:
        sheet = spreadsheet.worksheet(selected_month)
        records = sheet.get_all_values()
        if len(records) <= 1:
            st.info(text["no_data"])
            return
        header, *rows = records
        df = pd.DataFrame(rows, columns=header)
        key_col = "帳號" if "帳號" in df.columns else "姓名" if "姓名" in df.columns else None
        if not key_col:
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

        df["打卡時間"] = pd.to_datetime(df["日期"] + " " + df["時間"], errors='coerce')
        df = df.dropna(subset=["打卡時間"]).sort_values("打卡時間").head(100).reset_index(drop=True)
        df.index += 1
        df_display = df.drop(columns=["打卡時間"]).rename(columns=text["columns"])
        st.table(df_display)

        if is_admin:
            excel_buffer = io.BytesIO()
            df_display.to_excel(excel_buffer, index=False, sheet_name=selected_month)
            excel_buffer.seek(0)
            user_label = selected_user if selected_user != text["all_users_label"] else text["all_users_label"]
            filename = f"{selected_month}_{user_label}_{text['file_label']}.xlsx"
            st.download_button("📥 " + text["download"], data=excel_buffer, file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        st.error(f"{text['read_error']}{e}")

# --- 主功能邏輯區塊 ---
if is_admin:
    tab1, tab2 = st.tabs([text["admin_menu_options"]["view_records"], text["admin_menu_options"]["manage_accounts"]])
    with tab1:
        show_checkin_records()
    with tab2:
        tab_add, tab_view, tab_status = st.tabs([
            text["add_user"], text["all_users"], text["manage_user_status"]
        ])
        with tab_add:
            add_user(client, text)
        with tab_view:
            view_all_users(client, text)
        with tab_status:
            manage_user_status(client, text)
else:
    if st.button(text["checkin"]):
        check_in()
    show_checkin_records()
