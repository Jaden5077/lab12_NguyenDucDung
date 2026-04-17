FROM python:3.11-slim

WORKDIR /app

# Copy and install dependencies
COPY 05-scaling-reliability/production/utils /app/utils
RUN pip install --no-cache-dir fastapi uvicorn redis

# Copy app code
COPY 05-scaling-reliability/production/app.py /app/app.py

EXPOSE 8000

CMD ["python", "app.py"]
