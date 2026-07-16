# ESM3-open model server, reuses penstack:phase1.5 (torch + CUDA already present).
# Build ON THE VM: docker build -t penmodel:esm3 -f model_servers/esm3/Dockerfile .
FROM penstack:phase1.5

# EvolutionaryScale `esm` SDK (pulls ESM3-open weights on first use; ungated). FastAPI/uvicorn for the server.
RUN pip install --no-cache-dir fastapi uvicorn esm

ENV PYTHONUNBUFFERED=1 HF_HOME=/models/hf
WORKDIR /opt/server
COPY model_servers/esm3/server.py /opt/server/server.py

EXPOSE 9012
ENTRYPOINT ["uvicorn"]
CMD ["server:app", "--host", "0.0.0.0", "--port", "9012"]
