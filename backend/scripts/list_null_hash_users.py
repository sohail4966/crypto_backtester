#!/usr/bin/env python3
"""
Ops helper (BE-002 Solution C): list users with null password_hash.

Usage (from backend/):
  python -m scripts.list_null_hash_users
"""

from __future__ import annotations

from data.db import connect


def main() -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, email, name, created_at
                FROM app.users
                WHERE password_hash IS NULL
                ORDER BY created_at ASC
                """
            )
            rows = cur.fetchall()
    if not rows:
        print("No null-hash users found.")
        return
    print(f"Found {len(rows)} null-hash user(s):")
    for user_id, email, name, created_at in rows:
        print(f"  {user_id}  {email}  {name}  {created_at}")
    print("Set passwords via admin reset or ask users to re-register.")


if __name__ == "__main__":
    main()
