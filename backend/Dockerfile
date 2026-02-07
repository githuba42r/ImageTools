FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for image processing
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create storage directory
RUN mkdir -p /app/storage/temp

# Expose port
EXPOSE 8081

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081"]
