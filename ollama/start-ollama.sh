
#!/bin/sh
set -e

ollama serve &
OLLAMA_PID=$!

until ollama list >/dev/null 2>&1; do
  sleep 2
done

ollama pull qwen2.5vl:3b

wait "$OLLAMA_PID"
