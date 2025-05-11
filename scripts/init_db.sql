-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create monitored_urls table
CREATE TABLE monitored_urls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT NOT NULL,
    domain TEXT NOT NULL,
    title TEXT,
    priority INTEGER DEFAULT 1,
    check_frequency INTEGER NOT NULL DEFAULT 360, -- 6 hours in minutes
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_check TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT monitored_urls_url_unique UNIQUE (url)
);

-- Create price_history table
CREATE TABLE price_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url_id UUID NOT NULL REFERENCES monitored_urls(id) ON DELETE CASCADE,
    price DECIMAL(10,2),
    old_price DECIMAL(10,2),
    pix_price DECIMAL(10,2),
    installment_price JSONB DEFAULT '{}'::jsonb,
    availability TEXT,
    availability_text TEXT,
    shipping_info JSONB DEFAULT '{}'::jsonb,
    seller TEXT,
    promotion_labels TEXT[] DEFAULT '{}',
    promotion_end TIMESTAMP WITH TIME ZONE,
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    extraction_strategy_id UUID,
    extraction_confidence FLOAT,
    CONSTRAINT price_history_price_check CHECK (price >= 0),
    CONSTRAINT price_history_old_price_check CHECK (old_price >= 0),
    CONSTRAINT price_history_pix_price_check CHECK (pix_price >= 0)
);

-- Create scrape_logs table
CREATE TABLE scrape_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url_id UUID NOT NULL REFERENCES monitored_urls(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    message TEXT,
    error_type TEXT,
    extraction_time FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT scrape_logs_status_check CHECK (status IN ('success', 'error', 'warning', 'captcha', 'broken'))
);

-- Create extraction_strategies table
CREATE TABLE extraction_strategies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain TEXT NOT NULL,
    strategy_type TEXT NOT NULL,
    strategy_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    success_rate FLOAT DEFAULT 0,
    last_success TIMESTAMP WITH TIME ZONE,
    confidence_level FLOAT DEFAULT 0,
    priority INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sample_urls TEXT[] DEFAULT '{}',
    CONSTRAINT extraction_strategies_success_rate_check CHECK (success_rate >= 0 AND success_rate <= 1),
    CONSTRAINT extraction_strategies_confidence_level_check CHECK (confidence_level >= 0 AND confidence_level <= 1),
    CONSTRAINT extraction_strategies_strategy_type_check CHECK (strategy_type IN ('regex', 'xpath', 'css', 'semantic', 'ml', 'composite'))
);

-- Create aggregations table
CREATE TABLE aggregations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    value FLOAT NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT aggregations_period_check CHECK (period_end > period_start)
);

-- Create materialized views for common aggregations
CREATE MATERIALIZED VIEW mv_daily_price_stats AS
SELECT 
    url_id,
    date_trunc('day', checked_at) as day,
    min(price) as min_price,
    max(price) as max_price,
    avg(price) as avg_price,
    count(*) as checks_count
FROM price_history
GROUP BY url_id, date_trunc('day', checked_at);

CREATE MATERIALIZED VIEW mv_domain_stats AS
SELECT 
    domain,
    date_trunc('hour', checked_at) as hour,
    count(*) as total_checks,
    count(*) filter (where price is not null) as successful_checks,
    avg(extraction_confidence) as avg_confidence,
    avg(extraction_time) as avg_extraction_time
FROM price_history ph
JOIN monitored_urls mu ON ph.url_id = mu.id
GROUP BY domain, date_trunc('hour', checked_at);

-- Create partial indexes for common queries
CREATE INDEX idx_price_history_active_urls ON price_history(url_id)
WHERE checked_at > now() - interval '24 hours';

CREATE INDEX idx_price_history_domain_confidence ON price_history(url_id, extraction_confidence)
WHERE extraction_confidence > 0.8;

CREATE INDEX idx_monitored_urls_active_domain ON monitored_urls(domain)
WHERE active = true;

-- Partition price_history table by date
CREATE TABLE price_history_partitioned (
    LIKE price_history INCLUDING ALL
) PARTITION BY RANGE (checked_at);

-- Create partitions for current and next month
CREATE TABLE price_history_y2024m01 PARTITION OF price_history_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE price_history_y2024m02 PARTITION OF price_history_partitioned
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Create function to automatically create new partitions
CREATE OR REPLACE FUNCTION create_price_history_partition()
RETURNS trigger AS $$
DECLARE
    partition_date TEXT;
    partition_name TEXT;
BEGIN
    partition_date := to_char(NEW.checked_at, 'YYYY_MM');
    partition_name := 'price_history_' || partition_date;
    
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = partition_name) THEN
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF price_history_partitioned
             FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            date_trunc('month', NEW.checked_at),
            date_trunc('month', NEW.checked_at + interval '1 month')
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically create partitions
CREATE TRIGGER create_price_history_partition_trigger
    BEFORE INSERT ON price_history_partitioned
    FOR EACH ROW
    EXECUTE FUNCTION create_price_history_partition();

-- Create function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_price_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_price_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_domain_stats;
END;
$$ LANGUAGE plpgsql;

-- Create scheduled job to refresh materialized views
SELECT cron.schedule('0 * * * *', 'SELECT refresh_price_stats()');

-- Create indexes for better query performance

-- monitored_urls indexes
CREATE INDEX idx_monitored_urls_domain ON monitored_urls(domain);
CREATE INDEX idx_monitored_urls_active ON monitored_urls(active);
CREATE INDEX idx_monitored_urls_last_check ON monitored_urls(last_check);
CREATE INDEX idx_monitored_urls_priority ON monitored_urls(priority);

-- price_history indexes
CREATE INDEX idx_price_history_url_id ON price_history(url_id);
CREATE INDEX idx_price_history_checked_at ON price_history(checked_at);
CREATE INDEX idx_price_history_price ON price_history(price);
CREATE INDEX idx_price_history_extraction_strategy_id ON price_history(extraction_strategy_id);

-- scrape_logs indexes
CREATE INDEX idx_scrape_logs_url_id ON scrape_logs(url_id);
CREATE INDEX idx_scrape_logs_status ON scrape_logs(status);
CREATE INDEX idx_scrape_logs_created_at ON scrape_logs(created_at);
CREATE INDEX idx_scrape_logs_error_type ON scrape_logs(error_type);

-- extraction_strategies indexes
CREATE INDEX idx_extraction_strategies_domain ON extraction_strategies(domain);
CREATE INDEX idx_extraction_strategies_strategy_type ON extraction_strategies(strategy_type);
CREATE INDEX idx_extraction_strategies_confidence_level ON extraction_strategies(confidence_level);
CREATE INDEX idx_extraction_strategies_priority ON extraction_strategies(priority);

-- aggregations indexes
CREATE INDEX idx_aggregations_domain ON aggregations(domain);
CREATE INDEX idx_aggregations_metric_type ON aggregations(metric_type);
CREATE INDEX idx_aggregations_period ON aggregations(period_start, period_end);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for extraction_strategies
CREATE TRIGGER update_extraction_strategies_updated_at
    BEFORE UPDATE ON extraction_strategies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create function to validate price consistency
CREATE OR REPLACE FUNCTION validate_price_consistency()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure pix_price is not greater than regular price
    IF NEW.pix_price IS NOT NULL AND NEW.price IS NOT NULL AND NEW.pix_price > NEW.price THEN
        RAISE EXCEPTION 'PIX price cannot be greater than regular price';
    END IF;
    
    -- Ensure old_price is not less than current price
    IF NEW.old_price IS NOT NULL AND NEW.price IS NOT NULL AND NEW.old_price < NEW.price THEN
        RAISE EXCEPTION 'Old price cannot be less than current price';
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for price_history
CREATE TRIGGER validate_price_history_consistency
    BEFORE INSERT OR UPDATE ON price_history
    FOR EACH ROW
    EXECUTE FUNCTION validate_price_consistency();

-- Add RLS (Row Level Security) policies
ALTER TABLE monitored_urls ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE scrape_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE extraction_strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE aggregations ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Enable read access for all users" ON monitored_urls
    FOR SELECT USING (true);

CREATE POLICY "Enable read access for all users" ON price_history
    FOR SELECT USING (true);

CREATE POLICY "Enable read access for all users" ON scrape_logs
    FOR SELECT USING (true);

CREATE POLICY "Enable read access for all users" ON extraction_strategies
    FOR SELECT USING (true);

CREATE POLICY "Enable read access for all users" ON aggregations
    FOR SELECT USING (true);

-- Create service role policies for write access
CREATE POLICY "Enable write access for service role" ON monitored_urls
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Enable write access for service role" ON price_history
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Enable write access for service role" ON scrape_logs
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Enable write access for service role" ON extraction_strategies
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Enable write access for service role" ON aggregations
    FOR ALL USING (auth.role() = 'service_role');
