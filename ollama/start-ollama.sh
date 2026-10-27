
#!/bin/sh
set -e

ollama serve &
OLLAMA_PID=$!

until ollama list >/dev/null 2>&1; do
  sleep 2
done

if ! ollama list | grep -q 'qwen2.5vl:3b'; then
  ollama pull qwen2.5vl:3b
fi

ollama list

wait "$OLLAMA_PID"
