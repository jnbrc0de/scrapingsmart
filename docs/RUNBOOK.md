# Operations Runbook

## Standard Operating Procedures

### Daily Operations

#### 1. System Health Check
```bash
# Check service status
docker-compose ps

# Verify resource usage
docker stats

# Check error rates
curl -s http://localhost:9090/api/v1/query?query=rate\(scraper_errors_total[1h]\)
```

#### 2. Performance Monitoring
- Review Grafana dashboards
- Check queue size and processing rate
- Monitor resource utilization
- Verify proxy performance

#### 3. Data Quality Check
```sql
-- Check recent extractions
SELECT 
    date_trunc('hour', checked_at) as hour,
    count(*) as total,
    count(*) filter (where price is not null) as with_price,
    avg(extraction_confidence) as avg_confidence
FROM price_history
WHERE checked_at > now() - interval '24 hours'
GROUP BY 1
ORDER BY 1 DESC;
```

### Weekly Operations

#### 1. Database Maintenance
```sql
-- Analyze tables
ANALYZE monitored_urls;
ANALYZE price_history;
ANALYZE scrape_logs;

-- Update statistics
VACUUM ANALYZE;

-- Check index health
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

#### 2. Proxy Pool Maintenance
```bash
# Test all proxies
python scripts/test_proxies.py

# Update proxy list
python scripts/update_proxy_pool.py

# Verify geographic distribution
python scripts/analyze_proxy_distribution.py
```

#### 3. Performance Review
- Review weekly metrics
- Analyze error patterns
- Check resource utilization trends
- Update scaling parameters if needed

### Monthly Operations

#### 1. Security Updates
```bash
# Update base images
docker-compose pull

# Rebuild containers
docker-compose up -d --build

# Update SSL certificates if needed
certbot renew
```

#### 2. Backup Verification
```bash
# Test backup restoration
python scripts/verify_backup.py

# Validate backup integrity
python scripts/check_backup_integrity.py

# Update backup retention policy
python scripts/update_backup_policy.py
```

#### 3. Capacity Planning
- Review growth metrics
- Update resource allocations
- Plan infrastructure scaling
- Review cost optimization

## Emergency Procedures

### High Error Rate Response

#### Immediate Actions
1. Check error patterns:
```bash
docker-compose logs scraper | grep ERROR | sort | uniq -c | sort -nr
```

2. Verify proxy status:
```bash
python scripts/check_proxy_health.py
```

3. Check target site availability:
```bash
python scripts/verify_sites.py
```

#### Resolution Steps
1. If proxy issues:
```bash
# Rotate proxy pool
python scripts/rotate_proxies.py

# Update proxy configuration
python scripts/update_proxy_config.py
```

2. If rate limiting:
```bash
# Adjust request rates
python scripts/update_rate_limits.py

# Implement cooldown
python scripts/enable_cooldown.py
```

3. If site changes:
```bash
# Update extraction strategies
python scripts/update_strategies.py

# Retrain extractors
python scripts/retrain_extractors.py
```

### System Overload Response

#### Immediate Actions
1. Check resource usage:
```bash
docker stats --no-stream
```

2. Monitor queue size:
```bash
curl http://localhost:8000/metrics | grep queue_size
```

3. Check database load:
```sql
SELECT * FROM pg_stat_activity WHERE state = 'active';
```

#### Resolution Steps
1. Scale resources:
```bash
# Increase container resources
docker-compose up -d --scale scraper=5

# Adjust resource limits
python scripts/update_resource_limits.py
```

2. Reduce load:
```bash
# Pause non-critical scraping
python scripts/pause_low_priority.py

# Increase intervals
python scripts/adjust_intervals.py
```

3. Optimize performance:
```bash
# Enable caching
python scripts/enable_caching.py

# Optimize queries
python scripts/optimize_queries.py
```

### Data Quality Issues

#### Immediate Actions
1. Check extraction accuracy:
```sql
SELECT 
    domain,
    count(*) as total,
    avg(extraction_confidence) as confidence,
    count(*) filter (where price is null) as missing_price
FROM price_history ph
JOIN monitored_urls mu ON ph.url_id = mu.id
WHERE checked_at > now() - interval '1 hour'
GROUP BY domain
HAVING avg(extraction_confidence) < 0.8;
```

2. Verify extraction patterns:
```bash
python scripts/verify_extractors.py
```

3. Check for site changes:
```bash
python scripts/detect_site_changes.py
```

#### Resolution Steps
1. Update extractors:
```bash
# Generate new patterns
python scripts/generate_patterns.py

# Test new patterns
python scripts/test_patterns.py

# Deploy updates
python scripts/deploy_patterns.py
```

2. Retrain models:
```bash
# Collect training data
python scripts/collect_training_data.py

# Retrain models
python scripts/retrain_models.py

# Deploy models
python scripts/deploy_models.py
```

### Security Incident Response

#### Immediate Actions
1. Block suspicious IPs:
```bash
# Add to blocklist
python scripts/block_ips.py

# Update firewall rules
python scripts/update_firewall.py
```

2. Rotate credentials:
```bash
# Generate new keys
python scripts/rotate_keys.py

# Update configurations
python scripts/update_configs.py
```

3. Enable enhanced monitoring:
```bash
# Increase log level
python scripts/set_debug_logging.py

# Enable detailed tracking
python scripts/enable_tracking.py
```

#### Resolution Steps
1. Investigate incident:
```bash
# Analyze logs
python scripts/analyze_security_logs.py

# Track request patterns
python scripts/analyze_patterns.py
```

2. Implement fixes:
```bash
# Update security rules
python scripts/update_security.py

# Deploy patches
python scripts/deploy_patches.py
```

3. Document and report:
```bash
# Generate incident report
python scripts/generate_report.py

# Update security policies
python scripts/update_policies.py
```

## Maintenance Procedures

### Scheduled Maintenance

#### Pre-Maintenance
1. Notify stakeholders:
```bash
python scripts/send_maintenance_notice.py
```

2. Backup systems:
```bash
# Backup database
pg_dump -h host -U user -d dbname > pre_maintenance_backup.sql

# Backup configs
tar -czf config_backup.tar.gz config/
```

3. Reduce load:
```bash
python scripts/enable_maintenance_mode.py
```

#### During Maintenance
1. Stop services:
```bash
docker-compose down
```

2. Perform updates:
```bash
# Update images
docker-compose pull

# Apply migrations
python scripts/apply_migrations.py

# Update configurations
python scripts/update_configs.py
```

3. Verify systems:
```bash
# Start services
docker-compose up -d

# Run health checks
python scripts/verify_health.py
```

#### Post-Maintenance
1. Verify operations:
```bash
# Check all systems
python scripts/system_check.py

# Verify data flow
python scripts/verify_data_flow.py
```

2. Resume normal operations:
```bash
python scripts/disable_maintenance_mode.py
```

3. Send completion notice:
```bash
python scripts/send_completion_notice.py
```

### Emergency Maintenance

#### Quick Recovery
1. Stop affected services:
```bash
docker-compose stop scraper
```

2. Backup data:
```bash
python scripts/emergency_backup.py
```

3. Apply fixes:
```bash
python scripts/apply_emergency_fix.py
```

#### Service Restoration
1. Start services:
```bash
docker-compose up -d
```

2. Verify operation:
```bash
python scripts/verify_restoration.py
```

3. Monitor closely:
```bash
python scripts/enhanced_monitoring.py
``` 