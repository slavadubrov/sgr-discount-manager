"""Hybrid feature store for user context retrieval.

This module provides access to both hot (SQLite) and cold (DuckDB)
data stores for real-time and analytical user features.
"""

from .hybrid_store import HybridFeatureStore

__all__ = ["HybridFeatureStore"]
