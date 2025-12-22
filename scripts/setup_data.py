import sqlite3
import duckdb
import random
import os

DATA_DIR = "data"
SQL_DIR = "sgr/store/sql"


def load_sql(filename):
    with open(f"{SQL_DIR}/{filename}", "r") as f:
        return f.read()


def create_dummy_data():
    users = [f"user_{i}" for i in range(100, 110)]  # user_100 to user_109

    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # --- 1. Setup COLD Store (DuckDB) ---
    # Represents Historical Data (LTV, Churn) - Calculated Nightly
    print("🧊 Initializing Cold Store (DuckDB)...")
    db_path = os.path.join(DATA_DIR, "offline_store.duckdb")
    con_duck = duckdb.connect(db_path)
    con_duck.execute(load_sql("setup_duckdb.sql"))

    # Generate random historical profiles
    insert_sql = load_sql("insert_analytics.sql")
    for uid in users:
        # Randomize: Some users are "High Value/High Risk" (Targets for discounts)
        ltv = round(random.uniform(50.0, 5000.0), 2)
        churn = round(random.random(), 2)
        days = random.randint(5, 60)

        # Manually format for duckdb execute if binding issue exists, but binding is safer.
        # Original code used f-string for duckdb, let's switch to binding if possible or stick to f-string if query is simple.
        # But wait, extract used ? placeholders. DuckDB Python API supports standard placeholders.
        con_duck.execute(insert_sql, [uid, ltv, churn, days])

    con_duck.close()

    # --- 2. Setup HOT Store (SQLite) ---
    # Represents Real-Time Data (Cart, Margin) - Changes Millisecond by Millisecond
    print("🔥 Initializing Hot Store (SQLite)...")
    sql_path = os.path.join(DATA_DIR, "online_store.db")
    con_sql = sqlite3.connect(sql_path)
    cursor = con_sql.cursor()
    cursor.executescript(
        load_sql("setup_sqlite.sql")
    )  # executescript for multi-statement

    # Generate random active sessions
    inventory_levels = ["High", "Normal", "Low", "Critical"]
    insert_session_sql = load_sql("insert_session.sql")
    for uid in users:
        cart = round(random.uniform(20.0, 800.0), 2)
        margin = round(random.uniform(0.05, 0.40), 2)  # 5% to 40% margin
        inv = random.choice(inventory_levels)

        cursor.execute(insert_session_sql, (uid, cart, margin, inv))

    con_sql.commit()
    con_sql.close()
    print("✅ Databases populated with dummy data.")


if __name__ == "__main__":
    create_dummy_data()
