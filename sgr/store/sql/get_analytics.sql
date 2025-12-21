SELECT
    user_ltv,
    churn_probability
FROM user_analytics
WHERE user_id = ?
