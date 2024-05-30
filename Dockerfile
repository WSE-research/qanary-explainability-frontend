FROM ubuntu:22.04

ENV SERVER_PORT=8501
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -yq bash curl wget ca-certificates python3 python3-pip

# copy the application files
COPY . /app
WORKDIR /app

# install python dependencies
RUN python3 --version
RUN python3 -m pip install --upgrade pip 
RUN python3 -m pip install -r requirements.txt

EXPOSE $SERVER_PORT

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["sh","-c", "streamlit run explanation_frontend.py --server.port=$SERVER_PORT --server.address=0.0.0.0"]