import streamlit as st
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

info = dict(st.secrets["google_service_account"])
# info["private_key"] = info["private_key"].replace("\\n", "\n")

credentials = Credentials.from_service_account_info(info, scopes=scope)
client = gspread.authorize(credentials)
spreadsheet = client.open("打卡紀錄")
sheet = spreadsheet.sheet1

st.set_page_config(page_title="線上打卡系統", page_icon="🕘")
st.title("🕘 線上打卡系統（雲端 Google Sheets 版）")

name = st.text_input("請輸入您的名字")
if st.button("✅ 我要打卡"):
    if name.strip() == "":
        st.warning("⚠️ 請輸入有效的名字")
    else:
        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")
        sheet.append_row([name, date, time])
        st.success(f"🎉 打卡成功！時間：{date} {time}")
