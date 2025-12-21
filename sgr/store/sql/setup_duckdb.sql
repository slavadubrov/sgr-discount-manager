DROP TABLE IF EXISTS user_analytics;
CREATE TABLE user_analytics (
    user_id VARCHAR PRIMARY KEY,
    user_ltv DOUBLE,            -- Lifetime Value
    churn_probability DOUBLE,   -- ML Score (0.0 - 1.0)
    avg_days_between_orders INTEGER
);
