import streamlit as st
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import json
import requests
from google.cloud import secretmanager
from admin_user_management import manage_accounts
from streamlit.components.v1 import html as components_html

# --- 初始 session_state ---
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

# --- 頁面標題與 icon 設定 ---
is_admin = st.session_state.get("role", "user") == "admin"
title_key = "title_admin" if is_admin else "title_user"
st.set_page_config(page_title=text[title_key], page_icon="🕘")
st.title(text[title_key])

# --- 登入流程封裝 ---
def login_flow():
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

# --- 語言切換 + 登出按鈕（橫向排列＋樣式） ---
toggle_lang = "English" if st.session_state["language"] == "中文" else "中文"
logout_label = "🚪 登出" if st.session_state["language"] == "中文" else "🚪 Logout"

components_html(f"""
    <style>
    .top-buttons {{
        display: flex;
        gap: 10px;
        margin-top: 10px;
        margin-bottom: 20px;
    }}
    .top-buttons button {{
        padding: 6px 16px;
        font-size: 14px;
        border-radius: 6px;
        border: 1px solid #ddd;
        background-color: #f7f7f7;
        cursor: pointer;
    }}
    .top-buttons button.logout {{
        background-color: #ffecec;
        color: red;
        border: 1px solid #f3c2c2;
    }}
    </style>
    <div class="top-buttons">
        <form action="?lang=1" method="get">
            <button type="submit">{toggle_lang}</button>
        </form>
        {"" if not st.session_state.get("logged_in") else f'''<form action="?logout=1" method="get">
            <button class="logout" type="submit">{logout_label}</button>
        </form>'''}
    </div>
""", height=70)

# --- URL 控制行為 ---
params = st.query_params
if "lang" in params:
    st.session_state["language"] = toggle_lang
    st.query_params.clear()
    st.rerun()
elif "logout" in params:
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()

# --- 執行登入流程 ---
if not st.session_state["logged_in"]:
    login_flow()

# --- 功能選單 ---
st.divider()
st.markdown("### " + text["main_menu_title"])

# --- 管理者功能 ---
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
