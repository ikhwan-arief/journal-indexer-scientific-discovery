FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

COPY requirements-api.txt ./
RUN python -m pip install --no-cache-dir -r requirements-api.txt

COPY src ./src

EXPOSE 8000

CMD ["uvicorn", "journal_discovery_llm_api.app:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]

