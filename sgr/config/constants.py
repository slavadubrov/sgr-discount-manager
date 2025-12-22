"""Application constants and configuration values.

This module centralizes all magic values, thresholds, and configuration
constants used throughout the application. Following the principle of
single source of truth, all hardcoded values should be defined here.
"""

# =============================================================================
# API Configuration
# =============================================================================
DEFAULT_API_BASE_URL: str = "http://localhost:8000/v1"
"""Base URL for the vLLM OpenAI-compatible API server."""

DEFAULT_API_KEY: str = "EMPTY"
"""API key for vLLM server (EMPTY for local deployment)."""

DEFAULT_MODEL: str = "Qwen/Qwen2.5-1.5B-Instruct"
"""Fallback model ID if auto-detection fails."""

DEFAULT_TEMPERATURE: float = 0.1
"""Temperature for LLM inference (low for deterministic responses)."""

# =============================================================================
# Data Paths
# =============================================================================
DATA_DIR: str = "data"
"""Directory for database files."""

OFFLINE_STORE_PATH: str = "data/offline_store.duckdb"
"""Path to DuckDB analytical (cold) store."""

ONLINE_STORE_PATH: str = "data/online_store.db"
"""Path to SQLite operational (hot) store."""

SQL_DIR: str = "sgr/store/sql"
"""Directory containing SQL query files."""

# =============================================================================
# Business Rules - Churn Thresholds
# =============================================================================
HIGH_CHURN_THRESHOLD: float = 0.7
"""Churn probability above which aggressive discounts are offered."""

LOW_CHURN_THRESHOLD: float = 0.3
"""Churn probability below which minimal discounts are offered."""

# =============================================================================
# Business Rules - Default Values
# =============================================================================
DEFAULT_CHURN_PROBABILITY: float = 0.5
"""Default churn probability when data is unavailable."""

DEFAULT_CART_VALUE: float = 100.0
"""Default cart value in dollars when data is unavailable."""

DEFAULT_PROFIT_MARGIN: float = 0.2
"""Default profit margin (20%) when data is unavailable."""
