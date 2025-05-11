# Troubleshooting Guide

## Quick Reference

### System Status Check
```bash
# Check all containers
docker-compose ps

# View logs
docker-compose logs -f

# Check resource usage
docker stats
```

## Common Issues and Solutions

### 1. Scraping Failures

#### High Error Rates
**Symptoms:**
- Error rate > 10% in monitoring dashboard
- Increased failed requests in logs
- Alert notifications for high error rates

**Solutions:**
1. Check proxy health:
```bash
curl --proxy your-proxy-url:port http://httpbin.org/ip
```

2. Verify target site accessibility:
```bash
curl -I https://target-site.com
```

3. Review error patterns in logs:
```bash
docker-compose logs scraper | grep ERROR
```

4. Adjust retry settings in `config/settings.py`:
```python
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = 2
```

#### CAPTCHA Detection
**Symptoms:**
- Increased CAPTCHA responses
- Blocked requests
- Low success rate for specific domains

**Solutions:**
1. Rotate proxies more frequently
2. Adjust browser fingerprinting
3. Reduce request frequency
4. Implement cooldown periods:
```python
DOMAIN_COOLDOWN = 3600  # 1 hour
CAPTCHA_BACKOFF = 7200  # 2 hours
```

### 2. Performance Issues

#### High CPU Usage
**Symptoms:**
- Container CPU usage > 80%
- Slow response times
- Queued requests building up

**Solutions:**
1. Check resource usage:
```bash
docker stats scraper
```

2. Adjust container limits:
```yaml
# docker-compose.yml
services:
  scraper:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

3. Scale horizontally:
```bash
docker-compose up -d --scale scraper=3
```

#### Memory Leaks
**Symptoms:**
- Increasing memory usage over time
- Container restarts
- Out of memory errors

**Solutions:**
1. Monitor memory usage:
```bash
docker stats --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

2. Check for memory leaks:
```bash
# Enable memory profiling
export MEMORY_PROFILING=1
docker-compose restart scraper
```

3. Analyze memory dumps:
```bash
python -m memory_profiler scripts/analyze_memory.py
```

### 3. Database Issues

#### Connection Problems
**Symptoms:**
- Database connection errors
- Failed queries
- Timeout errors

**Solutions:**
1. Verify connection:
```bash
psql -h your-supabase-host -U postgres -d your-database -c "\dt"
```

2. Check connection limits:
```sql
SELECT * FROM pg_stat_activity;
```

3. Monitor connection pool:
```bash
docker-compose logs scraper | grep "connection pool"
```

#### Slow Queries
**Symptoms:**
- High query latency
- Database CPU spikes
- Timeout errors

**Solutions:**
1. Identify slow queries:
```sql
SELECT * FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
```

2. Add indexes:
```sql
CREATE INDEX idx_url_domain ON monitored_urls(domain);
CREATE INDEX idx_price_history_url_id ON price_history(url_id);
```

3. Optimize queries and implement caching

### 4. Monitoring Issues

#### Missing Metrics
**Symptoms:**
- Gaps in Grafana dashboards
- Missing data points
- Prometheus targets down

**Solutions:**
1. Check Prometheus targets:
```bash
curl http://localhost:9090/api/v1/targets
```

2. Verify metrics endpoints:
```bash
curl http://localhost:8000/metrics
```

3. Check Prometheus configuration:
```bash
docker-compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
```

#### Alert Failures
**Symptoms:**
- Missing alerts
- Delayed notifications
- False positives

**Solutions:**
1. Test alerting system:
```bash
curl -X POST http://localhost:9093/-/reload
```

2. Verify alert rules:
```bash
docker-compose exec prometheus promtool check rules /etc/prometheus/rules.yml
```

3. Check AlertManager configuration:
```bash
docker-compose exec alertmanager amtool check-config /etc/alertmanager/alertmanager.yml
```

### 5. Proxy Issues

#### High Proxy Failure Rate
**Symptoms:**
- Increased connection timeouts
- Proxy authentication errors
- Geographic restrictions

**Solutions:**
1. Test proxy connectivity:
```bash
for proxy in $(cat proxy_list.txt); do
  curl --proxy $proxy http://httpbin.org/ip
done
```

2. Rotate proxy pool:
```bash
python scripts/rotate_proxies.py
```

3. Adjust proxy settings:
```python
PROXY_ROTATION_INTERVAL = 300  # 5 minutes
PROXY_RETRY_ATTEMPTS = 3
PROXY_TIMEOUT = 10
```

## Diagnostic Tools

### Log Analysis
```bash
# Search for specific error patterns
docker-compose logs scraper | grep -A 5 -B 5 "ERROR"

# Count error occurrences
docker-compose logs scraper | grep ERROR | sort | uniq -c

# Monitor real-time errors
docker-compose logs -f scraper | grep ERROR
```

### Performance Monitoring
```bash
# CPU profiling
python -m cProfile -o output.prof src/scraper.py

# Memory profiling
python -m memory_profiler src/scraper.py

# Network monitoring
tcpdump -i any port 80 or port 443
```

### Database Diagnostics
```bash
# Connection status
SELECT * FROM pg_stat_activity;

# Table statistics
SELECT schemaname, relname, seq_scan, idx_scan 
FROM pg_stat_user_tables;

# Index usage
SELECT * FROM pg_stat_user_indexes;
```

## Recovery Procedures

### 1. Service Recovery
```bash
# Stop all services
docker-compose down

# Remove volumes (if needed)
docker-compose down -v

# Rebuild and restart
docker-compose up -d --build
```

### 2. Database Recovery
```bash
# Backup current state
pg_dump -h host -U user -d dbname > backup.sql

# Restore from backup
psql -h host -U user -d dbname < backup.sql
```

### 3. Configuration Recovery
```bash
# Backup configs
tar -czf config-backup.tar.gz config/

# Restore configs
tar -xzf config-backup.tar.gz
```

## Preventive Measures

1. Regular Health Checks
```bash
# Add to crontab
*/5 * * * * /usr/local/bin/docker-compose exec -T scraper python scripts/health_check.py
```

2. Automated Backups
```bash
# Daily database backup
0 0 * * * /usr/local/bin/docker-compose exec -T postgres pg_dump -U postgres > /backups/db-$(date +\%Y\%m\%d).sql
```

3. Log Rotation
```bash
# Configure logrotate
/var/log/scraper/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 scraper scraper
} 