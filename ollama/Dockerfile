
FROM ollama/ollama:latest

ENV OLLAMA_HOST=0.0.0.0:11434
ENV OLLAMA_MODEL=qwen2.5vl:3b

EXPOSE 11434

COPY start-ollama.sh /start-ollama.sh

RUN chmod +x /start-ollama.sh

ENTRYPOINT ["/usr/bin/bash", "/start-ollama.sh"]

