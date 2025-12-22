import sqlite3
import duckdb
from typing import Any


class HybridFeatureStore:
    def __init__(
        self, duck_path="data/offline_store.duckdb", sql_path="data/online_store.db"
    ):
        self.duck_path = duck_path
        self.sql_path = sql_path

    def _load_sql(self, filename: str) -> str:
        with open(f"sgr/store/sql/{filename}", "r") as f:
            return f.read()

    def _get_cold_data(self, user_id: str) -> dict[str, Any]:
        """Fetch analytical history from DuckDB."""
        try:
            query = self._load_sql("get_analytics.sql")
            # read_only=True allows concurrent access
            with duckdb.connect(self.duck_path, read_only=True) as con:
                row = con.execute(query, [user_id]).fetchone()
                return {"user_ltv": row[0], "churn_probability": row[1]} if row else {}
        except Exception as e:
            print(f"⚠️ DuckDB Error: {e}")
            return {}

    def _get_hot_data(self, user_id: str) -> dict[str, Any]:
        """Fetch live session state from SQLite."""
        try:
            query = self._load_sql("get_session.sql")
            with sqlite3.connect(self.sql_path) as con:
                cursor = con.cursor()
                row = cursor.execute(query, (user_id,)).fetchone()
                if row:
                    return {
                        "current_cart_value": row[0],
                        "cart_profit_margin": row[1],
                        "inventory_status": row[2],
                    }
                return {}
        except Exception as e:
            print(f"⚠️ SQLite Error: {e}")
            return {}

    def get_user_context(self, user_id: str) -> dict[str, Any]:
        """Merges Hot and Cold data into a single context vector."""
        cold = self._get_cold_data(user_id)
        hot = self._get_hot_data(user_id)

        # Merge dictionaries
        return {"user_id": user_id, **cold, **hot}
