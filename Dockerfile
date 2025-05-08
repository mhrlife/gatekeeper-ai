# Stage 1: Builder
# Use a lightweight Python base image for building
FROM python:3.12-slim-bookworm as builder

# Set working directory
WORKDIR /app

# Copy requirements.txt and install dependencies
# This layer is cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
# Use an even smaller base image for the final image
FROM python:3.12-slim-bookworm

# Set working directory
WORKDIR /app

# Copy installed dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the rest of the application code
COPY . .

# Expose the port if your application listens on one (adjust if needed)
# EXPOSE 8000

# Command to run the application
CMD ["python", "main.py"]
