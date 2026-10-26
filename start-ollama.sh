#!/bin/sh
set -eu

ollama serve &
server_pid=$!

# Wait for the API to become ready before pulling the model.
attempt=0
until ollama list >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 90 ]; then
    echo "Ollama did not become ready in time." >&2
    kill "$server_pid" 2>/dev/null || true
    exit 1
  fi
  sleep 2
done

# The Railway volume keeps model weights across restarts and redeploys.
ollama pull "${OLLAMA_MODEL:-qwen2.5vl:3b}"
wait "$server_pid"
