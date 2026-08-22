"""
One-time schema fix for EmpowerHR's database.db.

Adds the `employment_type` column to the existing `jobs` table.
This is required because `Base.metadata.create_all()` only creates tables
that don't exist yet -- it never alters an existing table's columns. Any
database created before `employment_type` was added to the `Job` model
needs this column added manually.

This script:
- Only touches the `jobs` table's schema (adds one column).
- Does NOT delete, drop, or recreate any table.
- Does NOT modify any existing row's data.
- Is safe to run multiple times (it checks state before acting, and does
  nothing if the fix has already been applied or doesn't apply).
"""

import sqlite3

DB_PATH = "database.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Confirm the jobs table exists.
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs';")
    if cur.fetchone() is None:
        print("jobs table does not exist -- nothing to fix. No changes made.")
        conn.close()
        return

    # 2. Confirm employment_type is actually missing.
    cur.execute("PRAGMA table_info(jobs);")
    columns = [row[1] for row in cur.fetchall()]
    if "employment_type" in columns:
        print("employment_type column already exists -- nothing to fix. No changes made.")
        conn.close()
        return

    # 3. Apply the fix. ADD COLUMN with a DEFAULT backfills existing rows
    #    in place -- no existing data is deleted or altered.
    print("jobs table found, employment_type is missing. Applying fix...")
    cur.execute(
        "ALTER TABLE jobs ADD COLUMN employment_type VARCHAR NOT NULL DEFAULT 'Full-time';"
    )
    conn.commit()
    print("Column added successfully.")
    conn.close()


if __name__ == "__main__":
    main()