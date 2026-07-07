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

CMD ["uvicorn", "app.web:app", "--host", "0.0.0.0", "--port", "8000"]
