import os
import time
from datetime import datetime, timedelta

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql

from config import DB_CONFIG
from reader import BlueForsLogReader


# Connect to the database
def connect_to_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("Database connection successful")
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None


# Ensure table exists dynamically
def ensure_table_exists(conn, table_name, columns):
    try:
        cursor = conn.cursor()
        column_definitions = ", ".join([f"{col} FLOAT" if col != "timestamp" else "timestamp TIMESTAMP NOT NULL" for col in columns])
        cursor.execute(
            sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    id SERIAL PRIMARY KEY,
                    {}
                );
            """).format(sql.Identifier(table_name), sql.SQL(column_definitions))
        )
        conn.commit()
        print(f"Ensured table {table_name} exists")
    except Exception as e:
        print(f"Error ensuring table {table_name} exists: {e}")
        conn.rollback()


# Insert data into the database
def insert_data_to_db(conn, table_name, data):
    try:
        cursor = conn.cursor()
        for _, row in data.iterrows():
            cols = list(row.index)
            query = sql.SQL("""
                INSERT INTO {} ({})
                VALUES ({})
                ON CONFLICT DO NOTHING;
            """).format(
                sql.Identifier(table_name),
                sql.SQL(", ").join(map(sql.Identifier, cols)),
                sql.SQL(", ").join(sql.Placeholder() for _ in cols)
            )
            cursor.execute(query, tuple(row))
        conn.commit()
        print(f"Inserted {len(data)} rows into {table_name}")
    except Exception as e:
        print(f"Error inserting data into {table_name}: {e}")
        conn.rollback()


# Monitor and update logs
def monitor_logs(log_reader, conn, log_types, folder_path, sleep_time=60):
    current_date = datetime.now().strftime('%y-%m-%d')

    while True:
        new_date = datetime.now().strftime('%y-%m-%d')

        # Check for date change and reset if needed
        if new_date != current_date:
            current_date = new_date

        # Process logs for the current day
        for log_type, table_name in log_types.items():
            data = log_reader.get_logs(current_date, log_type)
            if not data.empty:
                # Ensure table exists
                ensure_table_exists(conn, table_name, data.columns)
                # Insert data into the database
                insert_data_to_db(conn, table_name, data)

        time.sleep(sleep_time)


# Main function
def main():
    conn = connect_to_db()
    if conn is None:
        return

    log_reader = BlueForsLogReader(folder_path="./logs")

    # Define log types and corresponding tables
    log_types = {
        "temperature": "temperature",
        "pressure": "pressure",
        "resistance": "resistance",
        "status": "status",
        "flowmeter": "flowmeter"
    }

    try:
        monitor_logs(log_reader, conn, log_types, folder_path="./logs", sleep_time=30)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    finally:
        conn.close()
        print("Database connection closed")


if __name__ == "__main__":
    main()
