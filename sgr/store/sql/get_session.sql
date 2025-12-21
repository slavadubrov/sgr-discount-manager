SELECT
    current_cart_value,
    cart_profit_margin,
    inventory_status
FROM active_sessions
WHERE user_id = ?
