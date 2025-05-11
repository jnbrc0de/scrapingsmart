# API Documentation

## Overview
This document describes the REST API endpoints available in the Price Monitoring System.

## Base URL
```
https://api.scraper.yourdomain.com/v1
```

## Authentication
All API requests require an API key passed in the header:
```
Authorization: Bearer YOUR_API_KEY
```

## Endpoints

### URLs Management

#### List Monitored URLs
```http
GET /urls
```

**Query Parameters:**
- `domain` (optional): Filter by domain
- `status` (optional): Filter by status (active, paused, error)
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 50)

**Response:**
```json
{
  "urls": [
    {
      "id": "uuid",
      "url": "https://example.com/product",
      "domain": "example.com",
      "status": "active",
      "last_check": "2024-01-01T12:00:00Z",
      "check_frequency": 360
    }
  ],
  "total": 100,
  "page": 1,
  "per_page": 50
}
```

#### Add URL for Monitoring
```http
POST /urls
```

**Request Body:**
```json
{
  "url": "https://example.com/product",
  "check_frequency": 360,
  "priority": 1
}
```

**Response:**
```json
{
  "id": "uuid",
  "url": "https://example.com/product",
  "status": "active",
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Price History

#### Get Price History
```http
GET /prices/{url_id}
```

**Query Parameters:**
- `start_date`: Start date (ISO 8601)
- `end_date`: End date (ISO 8601)
- `aggregation`: none, daily, weekly, monthly

**Response:**
```json
{
  "prices": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "price": 99.90,
      "old_price": 129.90,
      "pix_price": 89.90,
      "availability": "in_stock"
    }
  ]
}
```

### System Status

#### Get System Metrics
```http
GET /metrics
```

**Response:**
```json
{
  "active_scrapers": 10,
  "queue_size": 100,
  "success_rate": 0.95,
  "avg_response_time": 2.5,
  "errors_last_hour": 5
}
```

### Error Codes

| Code | Description |
|------|-------------|
| 400  | Bad Request - Invalid parameters |
| 401  | Unauthorized - Invalid API key |
| 403  | Forbidden - Insufficient permissions |
| 404  | Not Found - Resource doesn't exist |
| 429  | Too Many Requests - Rate limit exceeded |
| 500  | Internal Server Error |

### Rate Limits
- 1000 requests per hour per API key
- Bulk operations count as multiple requests
- Status code 429 when exceeded

### Webhooks

#### Configure Webhook
```http
POST /webhooks
```

**Request Body:**
```json
{
  "url": "https://your-domain.com/webhook",
  "events": ["price_change", "availability_change"],
  "secret": "your-webhook-secret"
}
```

**Webhook Payload Example:**
```json
{
  "event": "price_change",
  "url_id": "uuid",
  "url": "https://example.com/product",
  "old_price": 129.90,
  "new_price": 99.90,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Best Practices

1. **Rate Limiting**
   - Implement exponential backoff
   - Cache frequently accessed data
   - Use bulk operations when possible

2. **Error Handling**
   - Always check error responses
   - Implement retry logic with backoff
   - Log all API interactions

3. **Security**
   - Store API keys securely
   - Use HTTPS for all requests
   - Validate webhook signatures

4. **Performance**
   - Use compression (gzip)
   - Implement request pooling
   - Cache responses when appropriate 