# Build stage
FROM golang:1.24.1-alpine AS builder

WORKDIR /workspace

# Copy Go module files first for better layer caching
COPY kubernetes-controller/go.mod kubernetes-controller/go.sum ./
RUN go mod download

# Copy the source code
COPY kubernetes-controller/ ./

# Build the controller binary
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -o manager cmd/manager/main.go

# Runtime stage
FROM gcr.io/distroless/static:nonroot

WORKDIR /

# Copy the controller binary from builder stage
COPY --from=builder /workspace/manager /manager

# Use nonroot user for security
USER 65532:65532

# Set entrypoint to the manager binary
ENTRYPOINT ["/manager"]
