"""
One-time schema fix for EmpowerHR's database.db (Step 9 — Employer System).

Adds the employer-related columns to the existing `users` and `jobs`
tables:

    users.role           VARCHAR NOT NULL DEFAULT 'candidate'
    users.company_name   VARCHAR
    jobs.employer_id     INTEGER REFERENCES users(id)
    jobs.is_active       BOOLEAN NOT NULL DEFAULT 1

This is required because `Base.metadata.create_all()` only creates
tables that don't exist yet -- it never alters an existing table's
columns. Any database created before these Step 9 fields were added to
the `User` / `Job` models needs these columns added manually.

This script:
- Only touches the `users` and `jobs` tables' schemas (adds columns).
- Does NOT drop or recreate any table.
- Does NOT delete or alter any existing row's data beyond the new
  column's default backfill (SQLite's ADD COLUMN ... DEFAULT backfills
  every existing row with that default value).
- Does NOT fabricate `employer_id` ownership for any existing job --
  jobs.employer_id has no DEFAULT, so existing rows get SQL NULL.
- Checks each column independently before acting, and is safe to run
  multiple times (skips any column that's already present).

Follows the exact pattern established by fix_profile_image_column.py
and fix_employment_type_column.py.
"""

import sqlite3

from database import DATA_DIR
import os

DB_PATH = os.path.join(DATA_DIR, "database.db")


def _table_exists(cur, table_name):
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
        (table_name,),
    )
    return cur.fetchone() is not None


def _column_exists(cur, table_name, column_name):
    cur.execute(f"PRAGMA table_info({table_name});")
    columns = [row[1] for row in cur.fetchall()]
    return column_name in columns


def _add_column_if_missing(cur, table_name, column_name, column_def):
    """Add `column_name` to `table_name` using `column_def` (the SQL
    fragment after the column name in ALTER TABLE ... ADD COLUMN) only if
    the table exists and the column is genuinely missing. Reports what it
    did (or why it did nothing) and returns True if a column was added."""
    if not _table_exists(cur, table_name):
        print(f"{table_name} table does not exist -- nothing to fix for "
              f"{table_name}.{column_name}. No changes made.")
        return False

    if _column_exists(cur, table_name, column_name):
        print(f"{table_name}.{column_name} already exists -- nothing to "
              f"fix. No changes made.")
        return False

    print(f"{table_name} table found, {column_name} is missing. "
          f"Applying fix...")
    cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def};")
    print(f"{table_name}.{column_name} added successfully.")
    return True


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    changed = False
    changed |= _add_column_if_missing(
        cur, "users", "role", "VARCHAR NOT NULL DEFAULT 'candidate'"
    )
    changed |= _add_column_if_missing(
        cur, "users", "company_name", "VARCHAR"
    )
    changed |= _add_column_if_missing(
        cur, "jobs", "employer_id", "INTEGER REFERENCES users(id)"
    )
    changed |= _add_column_if_missing(
        cur, "jobs", "is_active", "BOOLEAN NOT NULL DEFAULT 1"
    )

    if changed:
        conn.commit()
        print("Migration complete. Changes committed.")
    else:
        print("Migration complete. No changes were necessary.")

    conn.close()


if __name__ == "__main__":
    main()
