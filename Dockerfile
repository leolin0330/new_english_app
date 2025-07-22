# 使用 Python 精簡映像檔
FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 複製專案內容到容器內
COPY . .

# 安裝所需套件
RUN pip install --no-cache-dir -r requirements.txt

# 預設 port 為 Cloud Run 用的 8080
EXPOSE 8080

# 執行 Streamlit 主程式
CMD ["streamlit", "run", "check_in_app_test.py", "--server.port=8080", "--server.enableCORS=false"]
