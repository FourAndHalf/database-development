# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package.json and package-lock.json
COPY apps/ui/package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY apps/ui/ .

# Build the Angular application
RUN npm run build -- --configuration production

# Serve stage using Nginx
FROM nginx:alpine

# Copy the build output to replace the default nginx contents.
# Adjust 'database-rag-ui' if your angular.json specifies a different output path.
COPY --from=builder /app/dist/database-rag-ui/browser /usr/share/nginx/html

# Copy custom nginx configuration for routing to backend services
COPY apps/ui/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
