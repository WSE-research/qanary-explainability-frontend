FROM ubuntu:26.04

ENV SERVER_PORT=8501
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -yq bash curl wget ca-certificates python3 python3-venv

# copy the application files
COPY . /app
WORKDIR /app

# install python dependencies into an isolated virtualenv.
# Ubuntu 24.04+ marks the system Python as externally managed (PEP 668), so
# installing into the system interpreter is rejected; a venv avoids that.
# Putting the venv on PATH makes python/pip/streamlit resolve to it.
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN python3 --version
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE $SERVER_PORT

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["sh","-c", "streamlit run explanation_frontend.py --server.port=$SERVER_PORT --server.address=0.0.0.0"]