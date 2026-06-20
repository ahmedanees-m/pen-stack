# ProteinMPNN model server, reuses penstack:phase1.5 (torch 2.12 + CUDA already present).
# Build ON THE VM: docker build -t penmodel:proteinmpnn -f model_servers/proteinmpnn/Dockerfile .
FROM penstack:phase1.5

# ProteinMPNN is pure-PyTorch; clone it + its (small, bundled) vanilla weights. FastAPI/uvicorn for the server.
RUN pip install --no-cache-dir fastapi uvicorn \
 && git clone --depth 1 https://github.com/dauparas/ProteinMPNN /opt/ProteinMPNN

ENV PROTEINMPNN_DIR=/opt/ProteinMPNN PYTHONUNBUFFERED=1
WORKDIR /opt/server
COPY model_servers/proteinmpnn/server.py /opt/server/server.py

EXPOSE 9011
# bypass the base image's ollama entrypoint
ENTRYPOINT ["uvicorn"]
CMD ["server:app", "--host", "0.0.0.0", "--port", "9011"]
