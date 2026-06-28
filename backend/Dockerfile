FROM python:3.11-slim
WORKDIR /workspace
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /workspace/backend/requirements.txt
RUN pip install --no-cache-dir -r /workspace/backend/requirements.txt
ENV PYTHONPATH=/workspace
COPY backend/entrypoint.sh /workspace/backend/entrypoint.sh
RUN chmod +x /workspace/backend/entrypoint.sh
CMD ["/workspace/backend/entrypoint.sh"]
