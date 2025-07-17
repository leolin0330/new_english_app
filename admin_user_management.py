# admin帳號管理

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
                    st.warning("⚠️ 此帳號已存在，請使用其他帳號")
                elif not new_username or not new_password:
                    st.warning("⚠️ 請輸入完整帳號與密碼")
                else:
                    user_sheet.append_row([new_username, new_password, new_role, "Y" if enabled else "N"])
                    st.success(f"✅ 已新增帳號：{new_username}（角色：{new_role}）")
                    st.cache_data.clear()
            except Exception as e:
                st.error(f"❌ 新增帳號失敗：{e}")

def view_all_users(client):
    st.subheader("👥 所有使用者帳號")
    try:
        user_sheet = client.open("users_login").sheet1
        df_users = pd.DataFrame(user_sheet.get_all_records())
        if df_users.empty:
            st.info("尚無使用者資料")
        else:
            df_users_display = df_users.rename(columns={
                "帳號": "Account", "密碼": "Password", "角色": "Role", "是否啟用": "Enabled"
            })
            st.dataframe(df_users_display)
    except Exception as e:
        st.error(f"❌ 無法讀取帳號資料：{e}")

def delete_or_disable_user(client):
    st.subheader("🗑️ 刪除或停用帳號")
    try:
        user_sheet = client.open("users_login").sheet1
        users_data = user_sheet.get_all_records()
        df_users = pd.DataFrame(users_data)

        if df_users.empty:
            st.info("尚無使用者資料")
            return

        selected_account = st.selectbox("請選擇帳號", df_users["帳號"].tolist())
        action = st.radio("選擇操作", ["刪除帳號", "停用帳號"])

        if st.button("✅ 執行操作"):
            all_rows = user_sheet.get_all_values()
            header = all_rows[0]
            rows = all_rows[1:]
            if action == "刪除帳號":
                new_rows = [row for row in rows if row[0] != selected_account]
                user_sheet.clear()
                user_sheet.append_row(header)
                for row in new_rows:
                    user_sheet.append_row(row)
                st.success(f"✅ 已刪除帳號：{selected_account}")
            elif action == "停用帳號":
                for i in range(1, len(rows) + 1):
                    if rows[i - 1][0] == selected_account:
                        user_sheet.update_cell(i + 1, 4, "N")  # 第4欄是「是否啟用」
                        st.success(f"✅ 已停用帳號：{selected_account}")
                        break
            st.cache_data.clear()
            st.rerun()
    except Exception as e:
        st.error(f"❌ 操作失敗：{e}")
