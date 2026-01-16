# Frontend Dockerfile for OZX Image Atlas Tool

# Build stage
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (need all deps including devDeps for build)
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built application from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Create non-root user
RUN addgroup -g 1001 -S atlas && \
    adduser -S atlas -u 1001 -G atlas

# Set ownership
RUN chown -R atlas:atlas /usr/share/nginx/html && \
    chown -R atlas:atlas /var/cache/nginx && \
    chown -R atlas:atlas /var/log/nginx && \
    chown -R atlas:atlas /etc/nginx/conf.d

# Create necessary directories
RUN touch /var/run/nginx.pid && \
    chown -R atlas:atlas /var/run/nginx.pid

USER atlas

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]