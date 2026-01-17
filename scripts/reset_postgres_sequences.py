import argparse
import os

import sqlalchemy as sa


TABLES_WITH_IDS = [
    "users",
    "locations",
    "reviews",
    "saved_routes",
    "saved_places",
    "location_feedback",
    "route_feedback",
]


def main():
    parser = argparse.ArgumentParser(description="Reset Postgres sequences to MAX(id).")
    parser.add_argument("--postgres", default=os.environ.get("DATABASE_URL"), help="Postgres URL.")
    args = parser.parse_args()

    if not args.postgres:
        raise SystemExit("DATABASE_URL is required. Pass --postgres or set env var.")

    engine = sa.create_engine(args.postgres)
    with engine.begin() as conn:
        for table in TABLES_WITH_IDS:
            seq_stmt = sa.text(
                "SELECT setval(pg_get_serial_sequence(:table, 'id'), "
                "COALESCE(MAX(id), 1)) FROM " + table
            )
            conn.execute(seq_stmt, {"table": table})
            print(f"Reset sequence for {table}")


if __name__ == "__main__":
    main()
