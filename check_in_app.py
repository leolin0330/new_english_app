import streamlit as st
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 設定 Google Sheets API 權限
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["google_service_account"], scope)
client = gspread.authorize(creds)

# 開啟 Google Sheets（請確認名稱與你雲端試算表一致）
spreadsheet = client.open("打卡紀錄")
sheet = spreadsheet.sheet1

# Streamlit UI
st.set_page_config(page_title="線上打卡系統", page_icon="🕘")
st.title("🕘 線上打卡系統（雲端 Google Sheets 版）")

name = st.text_input("請輸入您的名字")
if st.button("✅ 我要打卡"):
    if name.strip() == "":
        st.warning("⚠️ 請輸入有效的名字")
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([name, now])
        st.success(f"🎉 打卡成功！時間：{now}")
