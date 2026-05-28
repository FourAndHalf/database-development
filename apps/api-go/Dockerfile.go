# Build stage
FROM golang:1.23-alpine AS builder

WORKDIR /app

# 1. Copy only go.mod and go.sum first to leverage layer caching
COPY apps/api-go/go.mod apps/api-go/go.sum ./apps/api-go/

# 2. Download dependencies
WORKDIR /app/apps/api-go
RUN go mod download

# 3. Copy the source code only after dependencies are downloaded
WORKDIR /app
COPY apps/api-go/ ./apps/api-go/

# 4. Build the Go app
WORKDIR /app/apps/api-go
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o main ./cmd/api

# Run stage
FROM alpine:latest

# Install runtime security certificates
RUN apk --no-cache add ca-certificates tzdata

WORKDIR /root/

# Copy only the compiled binary from the builder stage
COPY --from=builder /app/apps/api-go/main .

# Expose port 8080
EXPOSE 8080

# Command to run the executable
CMD ["./main"]
