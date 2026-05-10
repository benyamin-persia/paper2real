FROM python:3.13-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm curl ca-certificates \
    libnss3 libatk-bridge2.0-0 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libasound2t64 libpangocairo-1.0-0 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    (pip install --no-cache-dir -r requirements.txt || pip install --no-cache-dir -r requirements.txt --pre)
RUN playwright install chromium --with-deps
RUN chmod -R a+rx /ms-playwright

COPY . .
RUN npm install 2>/dev/null || true
RUN useradd --uid 1000 --create-home appuser || true
USER 1000

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
