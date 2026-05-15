FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential tesseract-ocr && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY packages ./packages
COPY apps/api ./apps/api
ENV PYTHONPATH=/app/apps/api:/app/packages/shared-types:/app/packages/resume-parser:/app/packages/ai-engine:/app/packages/scoring-engine
RUN pip install --no-cache-dir -e .[api]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "apps/api"]
