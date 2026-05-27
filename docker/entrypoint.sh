#!/bin/bash
set -e

# Start Ollama daemon
ollama serve &
OLLAMA_PID=$!
until curl -sf http://localhost:11434/api/tags > /dev/null; do
    sleep 1
done
echo "Ollama ready"

# Lazy-pull LLMs (only if not already present)
for model in "llama3.1:8b-instruct-q4_K_M" "phi3.5:3.8b-mini-instruct-q4_K_M"; do
    if ! ollama list | grep -q "${model%%:*}"; then
        echo "Pulling $model ..."
        ollama pull "$model"
    fi
done

case "${1:-streamlit}" in
    streamlit)
        exec streamlit run /workspace/pen-stack/pen_stack/server/app.py \
            --server.port 8501 --server.address 0.0.0.0
        ;;
    api)
        exec uvicorn pen_stack.api.main:app --host 0.0.0.0 --port 8000
        ;;
    monitor)
        exec python /workspace/pen-stack/scripts/run_monitor.py
        ;;
    bash)
        exec /bin/bash
        ;;
    *)
        exec "$@"
        ;;
esac
