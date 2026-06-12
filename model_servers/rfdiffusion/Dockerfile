# RFdiffusion model server — layers a FastAPI server on the rfdiffusion:base image (torch 1.12 + SE3 env).
# rfdiffusion:base is built ON THE VM first (docker/Dockerfile from RosettaCommons/RFdiffusion).
# Then: docker build -t penmodel:rfdiffusion -f model_servers/rfdiffusion/Dockerfile .
FROM rfdiffusion:base

# py3.9-compatible FastAPI/uvicorn (the base is python3.9). pydantic<2 to match the older stack.
# numpy<2 is REQUIRED: torch 1.12 is built against the numpy 1.x ABI; numpy 2.x -> "Numpy is not available".
RUN python3.9 -m pip install --no-cache-dir "numpy==1.23.5" "fastapi<0.100" "uvicorn" "pydantic<2"

ENV RFDIFFUSION_DIR=/app/RFdiffusion RFDIFFUSION_MODELS=/models PYTHONUNBUFFERED=1
WORKDIR /opt/server
COPY model_servers/rfdiffusion/server.py /opt/server/server.py

EXPOSE 9013
ENTRYPOINT ["uvicorn"]
CMD ["server:app", "--host", "0.0.0.0", "--port", "9013"]
