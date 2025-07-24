import streamlit as st
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import json
import requests
from google.cloud import secretmanager
from admin_user_management import manage_accounts

# --- 初始化狀態 ---
for key, value in {"language": "中文", "logged_in": False, "username": "", "role": "user"}.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- 快取 Secret ---
@st.cache_resource
def get_cached_secret(secret_id: str, version: str = "latest") -> dict:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/616566246123/secrets/{secret_id}/versions/{version}"
    response = client.access_secret_version(request={"name": name})
    return json.loads(response.payload.data.decode("UTF-8"))

# --- Google Sheets 認證 ---
@st.cache_resource
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    info = get_cached_secret("google_service_account")
    credentials = Credentials.from_service_account_info(info, scopes=scope)
    return gspread.authorize(credentials)

client = get_gspread_client()
spreadsheet = client.open("打卡紀錄")

# --- Google Sheets 共用工具 ---
def get_user_sheet():
    return client.open("users_login").sheet1

def get_user_records_df():
    return pd.DataFrame(get_user_sheet().get_all_records())

def get_current_time():
    return datetime.utcnow() + timedelta(hours=8)

# --- 語言載入 ---
@st.cache_resource
def load_translation_json(url: str):
    return requests.get(url).json()

lang = load_translation_json("https://raw.githubusercontent.com/leolin0330/new_english_app/main/lang_config.json")
text = lang[st.session_state["language"]]

# --- 使用者資料快取 ---
@st.cache_data(ttl=30)
def get_users_from_sheet():
    try:
        df = get_user_records_df()
        users_dict = {
            row["帳號"]: {
                "password": row["密碼"],
                "role": row.get("角色", "user"),
                "enabled": str(row.get("是否啟用", "Y")).strip().upper() == "Y"
            } for _, row in df.iterrows()
        }
        return users_dict
    except Exception as e:
        st.error(f"❌ {text.get('read_error', '無法讀取使用者資料表')}：{e}")
        return {}

# --- 頁面設定與標題 ---
st.set_page_config(page_title=text["title_admin"], page_icon="🕘")

# --- 語言與登出按鈕 + 登入流程 ---
toggle_lang = "English" if st.session_state["language"] == "中文" else "中文"
logout_label = "🚪 登出" if st.session_state["language"] == "中文" else "🚪 Logout"

if not st.session_state["logged_in"]:
    # 登入畫面：只顯示語言切換
    if st.button(toggle_lang):
        st.session_state["language"] = toggle_lang
        st.rerun()

    # 登入流程放這邊就夠了！
    users = get_users_from_sheet()
    username = st.text_input(text["username"])
    password = st.text_input(text["password"], type="password")
    if st.button(text["login"]):
        user_info = users.get(username)
        if not user_info:
            st.error(text["login_error"])
        elif not user_info["enabled"]:
            st.error(text.get("account_disabled", "⚠️ 該帳號已停用"))
        elif user_info["password"] != password:
            st.error(text["login_error"])
        else:
            st.session_state.update({
                "logged_in": True,
                "username": username,
                "role": user_info.get("role", "user")
            })
            st.toast(text["login_success"], icon="✅")
            st.rerun()
    st.stop()
else:
    # 登入後才顯示登出與語言切換（橫向排版）
    col1, col2 = st.columns(2)
    with col1:
        if st.button(toggle_lang):
            st.session_state["language"] = toggle_lang
            st.rerun()
    with col2:
        if st.button(logout_label):
            st.session_state.clear()
            st.rerun()

    # 登入後才顯示頁面內容
    st.title(text["title_admin"])
    st.divider()
    st.markdown("### " + text["main_menu_title"])

    # --- 管理者功能 ---
    is_admin = st.session_state.get("role") == "admin"
    if is_admin:
        menu_keys = text["admin_menu_keys"]
        if "admin_option_key" not in st.session_state:
            st.session_state["admin_option_key"] = menu_keys[0]

        with st.sidebar:
            st.header(text["admin_sidebar_header"])
            options = [text["admin_menu_options"][k] for k in menu_keys]
            selected_label = st.radio(text["select_function"], options, index=menu_keys.index(st.session_state["admin_option_key"]))
            selected_key = menu_keys[options.index(selected_label)]

            if selected_key != st.session_state["admin_option_key"]:
                st.session_state["admin_option_key"] = selected_key
                st.rerun()

        if st.session_state["admin_option_key"] == "view_records":
            from checkin_features import show_checkin_records
            show_checkin_records(spreadsheet, text, lang)
        elif st.session_state["admin_option_key"] == "manage_accounts":
            manage_accounts(client, text)

    # --- 使用者功能 ---
    if not is_admin:
        if st.button(text["checkin"]):
            from checkin_features import check_in
            check_in(spreadsheet, text)
        from checkin_features import show_checkin_records
        show_checkin_records(spreadsheet, text, lang)
