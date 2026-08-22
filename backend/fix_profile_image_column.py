"""
One-time schema fix for EmpowerHR's database.db.

Adds the `profile_image` column to the existing `users` table.
This is required because `Base.metadata.create_all()` only creates tables
that don't exist yet -- it never alters an existing table's columns. Any
database created before `profile_image` was added to the `User` model
(i.e. before Step 6 / the Profile Page) needs this column added manually,
or existing users will fail to log in / load their profile.

This script:
- Only touches the `users` table's schema (adds one nullable column).
- Does NOT delete, drop, or recreate any table.
- Does NOT modify any existing row's data (profile_image is left NULL
  for existing users, meaning "no photo uploaded yet").
- Is safe to run multiple times (it checks state before acting, and does
  nothing if the fix has already been applied or doesn't apply).
"""

import sqlite3

DB_PATH = "database.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Confirm the users table exists.
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
    if cur.fetchone() is None:
        print("users table does not exist -- nothing to fix. No changes made.")
        conn.close()
        return

    # 2. Confirm profile_image is actually missing.
    cur.execute("PRAGMA table_info(users);")
    columns = [row[1] for row in cur.fetchall()]
    if "profile_image" in columns:
        print("profile_image column already exists -- nothing to fix. No changes made.")
        conn.close()
        return

    # 3. Apply the fix. ADD COLUMN without a NOT NULL constraint backfills
    #    existing rows with NULL -- no existing data is deleted or altered,
    #    and existing users simply have no profile photo until they upload one.
    print("users table found, profile_image is missing. Applying fix...")
    cur.execute("ALTER TABLE users ADD COLUMN profile_image VARCHAR;")
    conn.commit()
    print("Column added successfully.")
    conn.close()


if __name__ == "__main__":
    main()
