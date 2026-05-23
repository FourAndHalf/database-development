# Build stage
FROM golang:1.23-alpine AS builder

WORKDIR /app

# Copy go mod and sum files
COPY apps/api-go-go/go.mod apps/api-go-go/go.sum ./apps/api-go-go/

# Download all dependencies. Dependencies will be cached if the go.mod and go.sum files are not changed
WORKDIR /app/apps/api-go-go
RUN go mod download

# Copy the source from the current directory to the Working Directory inside the container
WORKDIR /app
COPY apps/api-go-go/ ./apps/api-go-go/

# Build the Go app
WORKDIR /app/apps/api-go-go
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main ./cmd/api

# Run stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /root/

# Copy the Pre-built binary file from the previous stage
COPY --from=builder /app/apps/api-go-go/main .

# Expose port 8080 to the outside world
EXPOSE 8080

# Command to run the executable
CMD ["./main"]
