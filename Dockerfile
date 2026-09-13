FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

# Copy application files
COPY . .

# Expose port
EXPOSE 8000

# Start server
CMD ["python", "app.py"]
