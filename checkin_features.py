
import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
import gspread

# --- 取得當月工作表 ---
def get_sheet_for(spreadsheet, dt):
    sheet_name = dt.strftime("%Y%m")
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
        worksheet.append_row(["姓名", "日期", "時間"])
        return worksheet

# --- 打卡功能 ---
def check_in(spreadsheet, text):
    now = datetime.utcnow() + timedelta(hours=8)
    date = now.strftime("%Y/%m/%d")
    time = now.strftime("%H:%M:%S")
    sheet = get_sheet_for(spreadsheet, now)
    sheet.append_row([st.session_state["username"], date, time])
    st.success(f"{text['checkin_success']}{date} {time}")
    st.rerun()

# --- 查看紀錄 ---
def show_checkin_records(spreadsheet, text, lang):
    st.subheader(text["history_title"])

    @st.cache_data(ttl=60)
    def get_all_worksheets_titles():
        return [ws.title for ws in spreadsheet.worksheets() if ws.title.isdigit()]

    available_sheets = sorted(get_all_worksheets_titles())

    if not available_sheets:
        st.warning("⚠️ 尚無任何打卡工作表")
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

        if "帳號" in df.columns:
            key_col = "帳號"
        elif "姓名" in df.columns:
            key_col = "姓名"
        else:
            st.warning(text["missing_column"])
            return

        is_admin = st.session_state.get("role") == "admin"

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
        df_display = df.drop(columns=["打卡時間"], errors="ignore").rename(columns=column_map)
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
