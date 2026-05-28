# Build stage
FROM golang:1.23-alpine AS builder

WORKDIR /app

# Copy the entire project for context (or just the required app)
COPY . .

# Move to the Go API directory
WORKDIR /app/apps/api-go

# Download dependencies
RUN go mod download

# Build the Go app
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main ./cmd/api

# Run stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /root/

# Copy the Pre-built binary file from the builder stage
COPY --from=builder /app/apps/api-go/main .

# Expose port 8080 to the outside world
EXPOSE 8080

# Command to run the executable
CMD ["./main"]
