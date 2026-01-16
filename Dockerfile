# Combined Dockerfile for OZX Image Atlas Tool
# Combines frontend and backend into a single image

# Stage 1: Build frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .
RUN npm run build

# Stage 2: Final image with Python backend + built frontend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Pillow
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Copy nginx config for serving frontend and proxying API
RUN echo 'server { \n\
    listen 80; \n\
    server_name localhost; \n\
    \n\
    location / { \n\
        root /app/frontend/build; \n\
        index index.html; \n\
        try_files $uri $uri/ /index.html; \n\
    } \n\
    \n\
    location /v1/ { \n\
        proxy_pass http://127.0.0.1:8000; \n\
        proxy_set_header Host $host; \n\
        proxy_set_header X-Real-IP $remote_addr; \n\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \n\
        client_max_body_size 200M; \n\
    } \n\
    \n\
    location /health { \n\
        proxy_pass http://127.0.0.1:8000/; \n\
    } \n\
}' > /etc/nginx/sites-available/default

# Create startup script
RUN echo '#!/bin/bash \n\
cd /app/backend && uvicorn main:app --host 127.0.0.1 --port 8000 & \n\
nginx -g "daemon off;"' > /app/start.sh && chmod +x /app/start.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

EXPOSE 80

CMD ["/app/start.sh"]
