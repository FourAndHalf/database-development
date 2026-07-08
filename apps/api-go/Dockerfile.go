FROM golang:1.23-alpine AS builder

WORKDIR /src
COPY apps/api-go/go.mod apps/api-go/go.sum ./
RUN go mod download

COPY apps/api-go/ ./
RUN CGO_ENABLED=0 GOOS=linux go build -o /out/api ./cmd/api

FROM alpine:3.20

RUN apk add --no-cache ca-certificates wget

COPY --from=builder /out/api /usr/local/bin/api

EXPOSE 8081

ENTRYPOINT ["/usr/local/bin/api"]
