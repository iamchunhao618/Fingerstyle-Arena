FROM python:3.12-slim
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates curl git ffmpeg libsndfile1 default-jre-headless && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir numpy==2.2.6 scipy==1.15.3 soundfile==0.13.1 librosa==0.11.0 PyGuitarPro==0.11
WORKDIR /workspace
COPY original.wav /workspace/input/original.wav
COPY tools/ /workspace/tools/
RUN mkdir -p /workspace/output && chmod 444 /workspace/input/original.wav
