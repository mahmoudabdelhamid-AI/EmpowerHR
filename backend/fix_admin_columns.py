"""
One-time schema fix for EmpowerHR's database.db (Step 11 — Admin &
Moderation).

Adds the admin-moderation column to the existing `users` table:

    users.is_active   BOOLEAN NOT NULL DEFAULT 1

This is required because `Base.metadata.create_all()` only creates
tables that don't exist yet -- it never alters an existing table's
columns. Any database created before this Step 11 field was added to
the `User` model needs this column added manually.

This script:
- Only touches the `users` table's schema (adds one column).
- Does NOT drop or recreate any table.
- Does NOT delete or alter any existing row's data beyond the new
  column's default backfill (SQLite's ADD COLUMN ... DEFAULT backfills
  every existing row with that default value -- every existing user
  ends up is_active=1/True, i.e. still able to log in exactly as
  before this migration).
- Checks the column independently before acting, and is safe to run
  multiple times (skips the column if it's already present).

Follows the exact pattern established by fix_employer_columns.py.
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
        cur, "users", "is_active", "BOOLEAN NOT NULL DEFAULT 1"
    )

    if changed:
        conn.commit()
        print("Migration complete. Changes committed.")
    else:
        print("Migration complete. No changes were necessary.")

    conn.close()


if __name__ == "__main__":
    main()
