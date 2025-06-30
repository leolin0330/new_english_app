import streamlit as st
<<<<<<< HEAD
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["google_service_account"], scope)
client = gspread.authorize(creds)


spreadsheet = client.open("打卡紀錄")
sheet = spreadsheet.sheet1

# ====== Streamlit 介面 ======
=======
from datetime import datetime
import pandas as pd
import os

FILENAME = "打卡紀錄.csv"

>>>>>>> parent of d6f1341 (更改程式)
st.set_page_config(page_title="線上打卡系統", page_icon="🕘", layout="centered")
st.title("🕘 線上打卡系統")

name = st.text_input("請輸入您的名字..")
if st.button("✅ 我要打卡"):
    if name.strip() == "":
        st.warning("⚠️ 請輸入有效的名字")
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_record = pd.DataFrame([[name, now]], columns=["姓名", "打卡時間"])

        if os.path.exists(FILENAME):
            df = pd.read_csv(FILENAME)
            df = pd.concat([df, new_record], ignore_index=True)
        else:
            df = new_record

        df.to_csv(FILENAME, index=False, encoding="utf-8-sig")
        st.success(f"🎉 打卡成功！時間：{now}")