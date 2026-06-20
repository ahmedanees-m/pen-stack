# PEN-STACK v3.0, single project image, built ON THE VM from a CUDA base.
# Docker-only policy: nothing installs on the VM host; everything lives in this image.
FROM nvidia/cuda:12.2.0-cudnn8-runtime-ubuntu22.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 python3-pip git wget ca-certificates \
        zlib1g-dev libbz2-dev liblzma-dev libncurses5-dev && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /work
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
ENV PYTHONPATH=/work
# build: docker build -t penstack:0.1 -f docker/Dockerfile .
