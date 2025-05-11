# System Maintenance Guide

## Regular Maintenance Tasks

### Daily Maintenance

#### 1. Log Management
```bash
# Rotate logs
logrotate /etc/logrotate.d/scraper.conf

# Archive old logs
find /var/log/scraper -name "*.gz" -mtime +7 -exec mv {} /var/log/archive/ \;

# Check log sizes
du -sh /var/log/scraper/*
```

#### 2. Performance Monitoring
```bash
# Check system resources
htop
df -h
free -m

# Monitor container stats
docker stats --no-stream

# Check network usage
iftop -P
```

#### 3. Data Integrity
```sql
-- Verify recent data
SELECT 
    date_trunc('hour', checked_at) as hour,
    count(*) as records,
    count(distinct url_id) as unique_urls,
    count(*) filter (where price is null) as missing_price
FROM price_history
WHERE checked_at > now() - interval '24 hours'
GROUP BY 1
ORDER BY 1 DESC;

-- Check for anomalies
SELECT 
    url_id,
    price,
    old_price,
    checked_at
FROM price_history
WHERE price > old_price * 2 
    OR price < old_price * 0.5
ORDER BY checked_at DESC
LIMIT 10;
```

### Weekly Maintenance

#### 1. Database Optimization
```sql
-- Update statistics
ANALYZE verbose;

-- Clean up old data
DELETE FROM price_history 
WHERE checked_at < now() - interval '90 days';

-- Reclaim space
VACUUM FULL;

-- Reindex if needed
REINDEX TABLE price_history;
```

#### 2. Cache Management
```bash
# Clear Redis cache
redis-cli FLUSHDB

# Verify cache size
redis-cli INFO memory

# Optimize cache settings
python scripts/optimize_cache.py
```

#### 3. Proxy Maintenance
```bash
# Test proxy performance
python scripts/test_proxies.py

# Remove slow proxies
python scripts/clean_proxy_pool.py

# Update proxy list
python scripts/update_proxies.py
```

### Monthly Maintenance

#### 1. Security Updates
```bash
# Update system packages
apt update && apt upgrade -y

# Update Docker images
docker-compose pull
docker-compose build --pull

# Update Python dependencies
pip install --upgrade -r requirements.txt
```

#### 2. Performance Optimization
```bash
# Analyze slow queries
python scripts/analyze_query_performance.py

# Optimize indexes
python scripts/optimize_indexes.py

# Update query patterns
python scripts/update_query_patterns.py
```

#### 3. Configuration Review
```bash
# Audit configurations
python scripts/audit_configs.py

# Update thresholds
python scripts/update_thresholds.py

# Verify settings
python scripts/verify_settings.py
```

## System Optimization

### Database Optimization

#### 1. Index Management
```sql
-- Analyze index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Create missing indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS
    idx_price_history_checked_at 
    ON price_history (checked_at);

-- Remove unused indexes
DROP INDEX IF EXISTS unused_index_name;
```

#### 2. Query Optimization
```sql
-- Identify slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;

-- Optimize common patterns
CREATE MATERIALIZED VIEW mv_daily_stats AS
SELECT 
    date_trunc('day', checked_at) as day,
    count(*) as total_checks,
    avg(price) as avg_price
FROM price_history
GROUP BY 1;

-- Set up refresh
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_stats;
```

#### 3. Table Partitioning
```sql
-- Create partitioned table
CREATE TABLE price_history_partitioned (
    LIKE price_history
) PARTITION BY RANGE (checked_at);

-- Create partitions
CREATE TABLE price_history_y2024m01 
    PARTITION OF price_history_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Set up automatic partitioning
CREATE OR REPLACE FUNCTION create_partition_and_insert()
RETURNS trigger AS $$
BEGIN
    -- Partition creation logic
END;
$$ LANGUAGE plpgsql;
```

### Performance Tuning

#### 1. Resource Allocation
```yaml
# Update container resources
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

#### 2. Connection Pooling
```python
# Database pool configuration
DB_POOL_CONFIG = {
    'min_size': 10,
    'max_size': 50,
    'max_queries': 50000,
    'max_inactive_connection_lifetime': 300
}

# Redis pool configuration
REDIS_POOL_CONFIG = {
    'max_connections': 100,
    'timeout': 20,
    'retry_on_timeout': True
}
```

#### 3. Caching Strategy
```python
# Cache configuration
CACHE_CONFIG = {
    'default_timeout': 300,
    'key_prefix': 'scraper',
    'redis_url': 'redis://localhost:6379/0'
}

# Cache patterns
CACHE_PATTERNS = {
    'price_history': 3600,  # 1 hour
    'domain_stats': 86400,  # 1 day
    'proxy_list': 300      # 5 minutes
}
```

### Monitoring Optimization

#### 1. Metrics Configuration
```yaml
# Prometheus scrape config
scrape_configs:
  - job_name: 'scraper'
    metrics_path: '/metrics'
    scrape_interval: 15s
    static_configs:
      - targets: ['scraper:8000']

# Custom metrics
custom_metrics:
  - name: scraper_request_duration_seconds
    type: histogram
    buckets: [0.1, 0.5, 1.0, 2.0, 5.0]
  - name: scraper_errors_total
    type: counter
    labels: [error_type, domain]
```

#### 2. Alert Tuning
```yaml
# Alert rules
groups:
  - name: scraper_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(scraper_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
      - alert: SlowRequests
        expr: histogram_quantile(0.95, rate(scraper_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
```

#### 3. Dashboard Optimization
```json
{
  "dashboard": {
    "refresh": "1m",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "span": 6,
        "targets": [
          {
            "expr": "rate(scraper_requests_total[5m])",
            "legendFormat": "{{domain}}"
          }
        ]
      }
    ]
  }
}
```

## Maintenance Scripts

### 1. System Health Check
```python
#!/usr/bin/env python3

def check_system_health():
    """
    Comprehensive system health check
    """
    checks = [
        check_database_connection(),
        check_redis_connection(),
        check_proxy_pool(),
        check_queue_size(),
        check_error_rates(),
        check_resource_usage()
    ]
    return all(checks)

def generate_health_report():
    """
    Generate detailed health report
    """
    report = {
        'timestamp': datetime.now(),
        'status': check_system_health(),
        'metrics': collect_system_metrics(),
        'warnings': get_active_warnings(),
        'recommendations': generate_recommendations()
    }
    return report
```

### 2. Backup Management
```python
#!/usr/bin/env python3

def perform_backup():
    """
    Comprehensive backup procedure
    """
    # Backup database
    backup_database()
    
    # Backup configurations
    backup_configs()
    
    # Backup logs
    backup_logs()
    
    # Verify backup integrity
    verify_backups()

def verify_backups():
    """
    Verify backup integrity
    """
    # Check backup files
    check_backup_files()
    
    # Validate database dump
    validate_database_dump()
    
    # Test restoration
    test_restoration()
```

### 3. Performance Optimization
```python
#!/usr/bin/env python3

def optimize_performance():
    """
    Optimize system performance
    """
    # Analyze current performance
    current_metrics = analyze_performance()
    
    # Optimize database
    optimize_database()
    
    # Optimize cache
    optimize_cache()
    
    # Update configurations
    update_configurations()
    
    # Verify improvements
    verify_optimization()
```

## Best Practices

### 1. Resource Management
- Monitor resource usage trends
- Implement auto-scaling based on load
- Set appropriate resource limits
- Use resource quotas effectively

### 2. Data Management
- Implement data retention policies
- Regular backup verification
- Optimize data storage
- Monitor data quality

### 3. Security Management
- Regular security audits
- Update security patches
- Monitor security logs
- Maintain access controls

### 4. Performance Management
- Regular performance testing
- Optimize resource usage
- Monitor system metrics
- Update optimization strategies 