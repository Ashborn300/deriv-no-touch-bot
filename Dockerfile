FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
COPY bot_notouch.py .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "bot_notouch.py"]
