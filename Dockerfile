FROM python:3.12-slim

EXPOSE 8080

ADD requirements.txt requirements.txt

RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y \
    build-essential \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

ENV GOOGLE_APPLICATION_CREDENTIALS="application_default_credentials.json"

ENTRYPOINT ["streamlit", "run", "app2.py", "--server.port=8080", "--server.address=0.0.0.0"]