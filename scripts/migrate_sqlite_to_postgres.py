import argparse
import os
import sqlite3

import sqlalchemy as sa


TABLE_ORDER = [
    "users",
    "locations",
    "reviews",
    "saved_routes",
    "saved_route_locations",
    "saved_places",
    "location_feedback",
    "route_feedback",
]


def get_sqlite_rows(conn, table_name):
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    return cursor.fetchall()


def get_sqlite_columns(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def insert_rows(pg_conn, table_name, columns, rows):
    if not rows:
        return 0
    cols = ", ".join(columns)
    values = ", ".join([f":{col}" for col in columns])
    stmt = sa.text(f"INSERT INTO {table_name} ({cols}) VALUES ({values})")
    payload = [dict(row) for row in rows]
    pg_conn.execute(stmt, payload)
    return len(payload)


def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite data to Postgres.")
    parser.add_argument("--sqlite", default="app/data/data.sqlite", help="Path to SQLite database.")
    parser.add_argument("--postgres", default=os.environ.get("DATABASE_URL"), help="Postgres URL.")
    args = parser.parse_args()

    if not args.postgres:
        raise SystemExit("DATABASE_URL is required. Pass --postgres or set env var.")

    sqlite_conn = sqlite3.connect(args.sqlite)
    pg_engine = sa.create_engine(args.postgres)

    with pg_engine.begin() as pg_conn:
        try:
            pg_conn.execute(sa.text("ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(255)"))
        except Exception:
            pass
        for table in TABLE_ORDER:
            columns = get_sqlite_columns(sqlite_conn, table)
            rows = get_sqlite_rows(sqlite_conn, table)
            inserted = insert_rows(pg_conn, table, columns, rows)
            print(f"{table}: {inserted} rows")

    sqlite_conn.close()


if __name__ == "__main__":
    main()
