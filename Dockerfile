# Dockerfile

FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire app directory into /app
COPY app/ ./app/

# Set the entrypoint to run the main module
CMD ["python", "-m", "app.main"]
