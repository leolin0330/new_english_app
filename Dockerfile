FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .


EXPOSE 8501

CMD ["sh", "-c", "streamlit run check_in_app.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]
