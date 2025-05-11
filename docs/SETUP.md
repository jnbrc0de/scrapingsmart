# Setup Guide

## Prerequisites

### System Requirements
- Docker Engine 24.0+
- Docker Compose 2.20+
- 4GB RAM minimum (8GB recommended)
- 2 CPU cores minimum (4 cores recommended)
- 20GB disk space
- Linux/Unix-based OS (Ubuntu 22.04 LTS recommended)

### Required Services
- Supabase account and project
- Redis instance (can be deployed with Docker Compose)
- Prometheus/Grafana (included in Docker Compose)
- SMTP server for notifications
- Proxy service subscription (residential IPs)

## Installation Steps

### 1. Clone Repository
```bash
git clone https://github.com/your-org/price-scraper.git
cd price-scraper
```

### 2. Environment Setup

Create environment files for each environment:

```bash
# Development
cp .env.example .env.development

# Staging
cp .env.example .env.staging

# Production
cp .env.example .env.production
```

Configure the following variables in each .env file:

```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://localhost:6379/0

# Proxy Service
PROXY_SERVICE_URL=http://proxy-service
PROXY_API_KEY=your-api-key

# Monitoring
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=secure-password
PROMETHEUS_RETENTION=15d

# Scaling
MAX_INSTANCES=3
MAX_CPU_PERCENT=80.0
MAX_MEMORY_PERCENT=80.0

# Notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### 3. Database Initialization

```bash
# Connect to Supabase and run initialization script
psql -h your-supabase-host -U postgres -d your-database -f scripts/init_db.sql
```

### 4. Docker Setup

Build and start services:

```bash
# Development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Staging
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 5. Monitoring Setup

1. Access Grafana at http://your-server:3000
2. Login with admin credentials
3. Verify Prometheus data source is connected
4. Import dashboards from config/grafana/dashboards/

### 6. Security Configuration

1. Configure firewall rules:
```bash
# Allow only necessary ports
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

2. Setup SSL certificates:
```bash
# Using certbot with Docker
docker run -it --rm --name certbot \
  -v "/etc/letsencrypt:/etc/letsencrypt" \
  -v "/var/lib/letsencrypt:/var/lib/letsencrypt" \
  certbot/certbot certonly --standalone \
  -d your-domain.com
```

### 7. Proxy Configuration

1. Configure proxy rotation settings in `config/settings.py`
2. Test proxy connectivity:
```bash
curl --proxy your-proxy-url:port http://httpbin.org/ip
```

### 8. Scaling Configuration

Adjust resource limits in `docker-compose.yml`:

```yaml
services:
  scraper:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
```

### 9. Monitoring Verification

1. Check Prometheus targets:
```bash
curl http://localhost:9090/api/v1/targets
```

2. Verify metrics collection:
```bash
curl http://localhost:9090/api/v1/query?query=up
```

3. Test alerting:
```bash
# Trigger a test alert
curl -X POST http://localhost:9093/-/reload
```

## Post-Installation

### Health Check
```bash
# Check all services
docker-compose ps

# Verify logs
docker-compose logs -f

# Test API endpoint
curl http://localhost:8000/health
```

### Initial Data Load
```bash
# Load initial URLs for monitoring
python scripts/load_initial_urls.py

# Verify data in database
psql -h your-supabase-host -U postgres -d your-database -c "SELECT count(*) FROM monitored_urls;"
```

### Backup Configuration
```bash
# Backup all configuration
tar -czf config-backup.tar.gz config/

# Backup database
pg_dump -h your-supabase-host -U postgres -d your-database > backup.sql
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify Supabase credentials
   - Check network connectivity
   - Confirm IP whitelist settings

2. **Proxy Issues**
   - Test proxy connectivity
   - Verify API key validity
   - Check proxy rotation settings

3. **Resource Limits**
   - Monitor container resources
   - Adjust limits if needed
   - Check system capacity

### Verification Steps

1. **Database**
```bash
# Test connection
psql -h your-supabase-host -U postgres -d your-database -c "\dt"
```

2. **Redis**
```bash
# Test Redis
redis-cli ping
```

3. **Monitoring**
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets
```

## Next Steps

1. Configure alerting rules in Prometheus
2. Set up backup automation
3. Implement monitoring dashboards
4. Configure log rotation
5. Set up CI/CD pipeline 