FROM python:3.12-slim

WORKDIR /app

RUN addgroup --system --gid 1001 app \
    && adduser --system --uid 1001 --gid 1001 app

COPY requirements.txt .
RUN pip install --no-cache-dir --no-compile -r requirements.txt \
    && rm -rf /root/.cache/pip

COPY --chown=app:app . .

RUN mkdir downloads && chown app:app downloads

USER app

EXPOSE 8000

ENV DOWNLOAD_TTL=0

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "app.web:app", "--host", "0.0.0.0", "--port", "8000"]
