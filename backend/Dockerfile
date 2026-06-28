FROM python:3.11-slim
WORKDIR /workspace
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /workspace/backend/requirements.txt
RUN pip install --no-cache-dir -r /workspace/backend/requirements.txt
ENV PYTHONPATH=/workspace
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
