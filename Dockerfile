# Dhruva — momentum wealth engine. Portable container for any device.
#
#   Build:  docker build -t dhruva .
#   Serve the dashboard (http://localhost:8501):
#           docker run -p 8501:8501 dhruva
#   Run one daily update instead:
#           docker run dhruva python scripts/daily_run.py
#   With Telegram + LLM narrator:
#           docker run -e TELEGRAM_TOKEN=xxx -e TELEGRAM_CHAT=yyy \
#                      -e ANTHROPIC_API_KEY=zzz dhruva python scripts/daily_run.py
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501
# Default: serve the public dashboard. Override the command to run the daily update.
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
