
import streamlit as st
import pandas as pd

def add_user(client, text):
    st.subheader(text["add_user"])
    with st.form("add_user_form", clear_on_submit=True):
        new_username = st.text_input(text["new_account"])
        new_password = st.text_input(text["new_password"], type="password")
        new_role = st.selectbox(text["new_role"], options=["user", "admin"])
        enabled = st.checkbox(text["enabled"], value=True)
        submitted = st.form_submit_button(text["add_user_button"])
        if submitted:
            try:
                user_sheet = client.open("users_login").sheet1
                existing_users = [row["帳號"] for row in user_sheet.get_all_records()]
                if new_username in existing_users:
                    st.warning(text.get("account_exists", "⚠️ 此帳號已存在，請使用其他帳號"))
                elif not new_username or not new_password:
                    st.warning(text.get("input_required", "⚠️ 請輸入完整帳號與密碼"))
                else:
                    user_sheet.append_row([new_username, new_password, new_role, "Y" if enabled else "N"])
                    st.toast(f"{text.get('add_user_success', '✅ 已新增帳號')}：{new_username}（{new_role}）", icon="✅")
                    st.cache_data.clear()
            except Exception as e:
                st.error(f"{text.get('add_user_failed', '❌ 新增帳號失敗')}：{e}")

def view_all_users(client, text):
    st.subheader(text.get("all_users", "👥 所有使用者帳號"))
    try:
        user_sheet = client.open("users_login").sheet1
        df_users = pd.DataFrame(user_sheet.get_all_records())
        if df_users.empty:
            st.info(text.get("no_users", "尚無使用者資料"))
        else:
            df_users_display = df_users.rename(columns={
                "帳號": text.get("username", "帳號"),
                "密碼": text["password"],
                "角色": text["new_role"],
                "是否啟用": text["enabled"]
            })
            st.dataframe(df_users_display)
    except Exception as e:
        st.error(f"{text.get('read_error', '❌ 無法讀取帳號資料')}：{e}")

def manage_user_status(client, text):
    st.subheader(text.get("manage_user_status", "👤 帳號狀態管理"))
    try:
        user_sheet = client.open("users_login").sheet1
        users_data = user_sheet.get_all_records()
        df_users = pd.DataFrame(users_data)

        if df_users.empty:
            st.info(text.get("no_users", "尚無使用者資料"))
            return

        selected_account = st.selectbox(text.get("select_account", "請選擇帳號"), df_users["帳號"].tolist())
        action = st.radio(text.get("choose_action", "選擇操作"), [
            text.get("enable_account", "✅ 啟用帳號"),
            text.get("disable_account", "🚫 停用帳號"),
            text.get("delete_account", "🗑️ 刪除帳號")
        ])

        if st.button(text.get("execute_action", "✅ 執行操作")):
            all_rows = user_sheet.get_all_values()
            header = all_rows[0]
            rows = all_rows[1:]

            if action == text.get("delete_account", "🗑️ 刪除帳號"):
                new_rows = [row for row in rows if row[0] != selected_account]
                user_sheet.clear()
                user_sheet.append_row(header)
                for row in new_rows:
                    user_sheet.append_row(row)
                st.toast(f"{text.get('deleted_account', '✅ 已刪除帳號')}：{selected_account}", icon="✅")

            elif action == text.get("disable_account", "🚫 停用帳號"):
                for i, row in enumerate(rows, start=2):
                    if row[0] == selected_account:
                        user_sheet.update_cell(i, 4, "N")
                        st.toast(f"{text.get('disabled_account', '✅ 已停用帳號')}：{selected_account}", icon="🚫")
                        break

            elif action == text.get("enable_account", "✅ 啟用帳號"):
                for i, row in enumerate(rows, start=2):
                    if row[0] == selected_account:
                        user_sheet.update_cell(i, 4, "Y")
                        st.toast(f"{text.get('enabled_account', '✅ 已啟用帳號')}：{selected_account}", icon="✅")
                        break

            st.cache_data.clear()
            st.rerun()

    except Exception as e:
        st.error(f"{text.get('operation_failed', '❌ 操作失敗')}：{e}")

def manage_accounts(client, text):
    # 初始化 tab 狀態
    if "account_tab" not in st.session_state:
        st.session_state["account_tab"] = "add"

    tab_options = {
        "add": text.get("add_user", "新增帳號"),
        "view": text.get("all_users", "所有使用者帳號"),
        "status": text.get("manage_user_status", "帳號狀態管理")
    }

    selected_tab_label = st.radio("📁 功能選單", list(tab_options.values()),
                                  index=list(tab_options).index(st.session_state["account_tab"]))

    # 反查目前選到哪個 tab key
    selected_tab_key = [k for k, v in tab_options.items() if v == selected_tab_label][0]
    st.session_state["account_tab"] = selected_tab_key

    st.subheader("👤 " + tab_options[selected_tab_key])

    # 顯示對應的內容
    if selected_tab_key == "add":
        add_user(client, text)
    elif selected_tab_key == "view":
        view_all_users(client, text)
    elif selected_tab_key == "status":
        manage_user_status(client, text)
