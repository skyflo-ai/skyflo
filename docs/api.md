# Skyflo.ai API Documentation

This document provides information about the Skyflo.ai API endpoints, authentication, and usage.

## Base URL

```
https://api.skyflo.ai/v1
```

## Authentication

All API requests require authentication using the following header:

```
Authorization: Bearer <api_token>
```

## Endpoints

### 1. Generate Agent AuthKey

Generate a unique authentication key for a new agent installation.

**Endpoint:** `POST /agents/auth-key`

**Request Body:**
```json
{
    "customer_id": "string",
    "agent_type": "aws|kubernetes",
    "environment": "string"
}
```

**Response:**
```json
{
    "auth_key": "string",
    "expires_at": "ISO8601 timestamp",
    "agent_id": "string"
}
```

### 2. Agent Alive Ping & Initial Crawl

Endpoint for agents to notify they are alive and receive initial crawl instructions.

**Endpoint:** `POST /agents/{agent_id}/alive`

**Request Headers:**
```
X-Agent-Auth-Key: <auth_key>
```

**Request Body:**
```json
{
    "agent_type": "aws|kubernetes",
    "agent_version": "string",
    "system_info": {
        "os": "string",
        "architecture": "string",
        "cpu_cores": "number",
        "memory_total": "string"
    }
}
```

**Response:**
```json
{
    "status": "INITIATE_CRAWL",
    "crawl_id": "string",
    "crawl_config": {
        "scan_depth": "number",
        "resource_types": ["array of strings"],
        "excluded_paths": ["array of strings"]
    }
}
```

### 3. AWS Crawl Complete Webhook

Webhook endpoint for AWS agents to report crawl completion.

**Endpoint:** `POST /webhooks/aws/{agent_id}/crawl-complete`

**Request Headers:**
```
X-Agent-Auth-Key: <auth_key>
X-Crawl-ID: <crawl_id>
```

**Request Body:**
```json
{
    "crawl_stats": {
        "resources_scanned": "number",
        "start_time": "ISO8601 timestamp",
        "end_time": "ISO8601 timestamp",
        "resource_types_found": ["array of strings"]
    },
    "error_count": "number",
    "warnings": ["array of strings"]
}
```

**Response:**
```json
{
    "status": "accepted",
    "next_crawl_delay": "number (seconds)"
}
```

### 4. Kubernetes Crawl Complete Webhook

Webhook endpoint for Kubernetes agents to report crawl completion.

**Endpoint:** `POST /webhooks/kubernetes/{agent_id}/crawl-complete`

**Request Headers:**
```
X-Agent-Auth-Key: <auth_key>
X-Crawl-ID: <crawl_id>
```

**Request Body:**
```json
{
    "crawl_stats": {
        "clusters_scanned": "number",
        "namespaces_scanned": "number",
        "start_time": "ISO8601 timestamp",
        "end_time": "ISO8601 timestamp",
        "resource_types_found": ["array of strings"]
    },
    "error_count": "number",
    "warnings": ["array of strings"]
}
```

**Response:**
```json
{
    "status": "accepted",
    "next_crawl_delay": "number (seconds)"
}
```

### 5. AWS Continuous Crawl Webhook

Webhook endpoint for AWS agents to report continuous crawl updates.

**Endpoint:** `POST /webhooks/aws/{agent_id}/continuous-crawl`

**Request Headers:**
```
X-Agent-Auth-Key: <auth_key>
```

**Request Body:**
```json
{
    "timestamp": "ISO8601 timestamp",
    "changes_detected": [{
        "resource_type": "string",
        "change_type": "created|modified|deleted",
        "resource_id": "string",
        "details": "object"
    }],
    "metrics": {
        "cpu_usage": "number",
        "memory_usage": "number",
        "network_usage": "object"
    }
}
```

**Response:**
```json
{
    "status": "accepted",
    "config_updates": {
        "scan_frequency": "number (seconds)",
        "resource_focus": ["array of strings"]
    }
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
    "error": "string",
    "message": "string",
    "details": "object (optional)"
}
```

### 401 Unauthorized
```json
{
    "error": "unauthorized",
    "message": "Invalid or expired authentication credentials"
}
```

### 429 Too Many Requests
```json
{
    "error": "rate_limit_exceeded",
    "message": "Too many requests",
    "retry_after": "number (seconds)"
}
```

### 500 Internal Server Error
```json
{
    "error": "internal_server_error",
    "message": "An unexpected error occurred",
    "request_id": "string"
}
```

## Rate Limits

- Authentication key generation: 10 requests per minute per customer
- Agent alive ping: 1 request per minute per agent
- Webhooks: 60 requests per minute per agent

## Security Considerations

1. All endpoints must be accessed over HTTPS
2. Auth keys should be rotated every 30 days
3. Failed authentication attempts are logged and monitored
4. Request payloads are limited to 10MB
5. All requests must include appropriate content-type headers 