# Multi-stage build for production
FROM node:24-alpine as builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies (including dev deps for building)
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built application from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configurations
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY nginx-main.conf /etc/nginx/nginx.conf

# Create non-root user for nginx
RUN addgroup -g 1001 -S flyesports \
    && adduser -S flyesports -u 1001

# Create directories and set permissions
RUN mkdir -p /var/cache/nginx /var/log/nginx /var/run/nginx \
    && chown -R flyesports:flyesports /usr/share/nginx/html \
    && chown -R flyesports:flyesports /var/cache/nginx \
    && chown -R flyesports:flyesports /var/log/nginx \
    && chown -R flyesports:flyesports /etc/nginx/conf.d \
    && touch /var/run/nginx.pid \
    && chown -R flyesports:flyesports /var/run/nginx.pid

USER flyesports

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]