FROM python:3.12-slim

WORKDIR /app

RUN pip install pip -U

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENV DOWNLOAD_TTL=0

CMD ["uvicorn", "app.web:app", "--host", "0.0.0.0", "--port", "8000"]
