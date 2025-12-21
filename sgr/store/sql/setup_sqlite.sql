DROP TABLE IF EXISTS active_sessions;
CREATE TABLE active_sessions (
    user_id TEXT PRIMARY KEY,
    current_cart_value REAL,
    cart_profit_margin REAL,    -- e.g., 0.20 for 20%
    inventory_status TEXT       -- 'High', 'Low', 'Critical'
);
