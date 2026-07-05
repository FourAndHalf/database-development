# Build stage
FROM golang:1.23-alpine AS builder

WORKDIR /app

# Copy only dependency files
COPY apps/api-go/go.mod apps/api-go/go.sum ./apps/api-go/

# Download dependencies
WORKDIR /app/apps/api-go
RUN go mod download

# SURGICAL COPY: Only copy the Go source
WORKDIR /app
COPY apps/api-go/ ./apps/api-go/

# Build
WORKDIR /app/apps/api-go
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o main ./cmd/api

# Run stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /root/

# Copy ONLY the binary
COPY --from=builder /app/apps/api-go/main .

EXPOSE 8080

CMD ["./main"]
