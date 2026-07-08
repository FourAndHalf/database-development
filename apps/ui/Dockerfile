FROM node:20-alpine AS builder

WORKDIR /src
COPY apps/ui/package.json apps/ui/package-lock.json ./
RUN npm ci

COPY apps/ui/ ./
RUN npm run build

FROM nginx:alpine

COPY --from=builder /src/dist/database-rag-ui/browser /usr/share/nginx/html
COPY apps/ui/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
