FROM ollama/ollama:0.32.5

ENV OLLAMA_HOST=[::]:11434 \
    OLLAMA_MODELS=/root/.ollama/models \
    OLLAMA_NO_CLOUD=1 \
    OLLAMA_CONTEXT_LENGTH=4096 \
    OLLAMA_KEEP_ALIVE=5m \
    OLLAMA_NUM_PARALLEL=1 \
    OLLAMA_MAX_LOADED_MODELS=1 \
    OLLAMA_MODEL=qwen2.5vl:3b

EXPOSE 11434
COPY start-ollama.sh /start-ollama.sh
RUN chmod +x /start-ollama.sh
CMD ["/start-ollama.sh"]
