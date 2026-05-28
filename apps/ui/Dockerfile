# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files first for better caching
COPY apps/ui/package*.json ./

# Install dependencies (frozen for speed and reliability)
RUN npm ci

# Copy the rest of the application code
COPY apps/ui/ .

# Build the Angular application
RUN npm run build -- --configuration production

# Serve stage using Nginx
FROM nginx:stable-alpine

# Copy built files
COPY --from=builder /app/dist/database-rag-ui/browser /usr/share/nginx/html

# Copy custom nginx configuration
COPY apps/ui/nginx.conf /etc/nginx/conf.d/default.conf

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
