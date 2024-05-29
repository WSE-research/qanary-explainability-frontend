FROM python:3.9-slim

ENV SERVER_PORT=8501

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# copy the application files
COPY . /app
WORKDIR /app

RUN python3 -m pip install -r requirements.txt

EXPOSE $SERVER_PORT

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["sh","-c", "streamlit run explanation_frontend.py --server.port=$SERVER_PORT --server.address=0.0.0.0"]