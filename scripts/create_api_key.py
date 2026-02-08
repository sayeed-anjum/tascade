#!/usr/bin/env python3
"""Bootstrap script to create an API key directly in the database.

Usage:
    python scripts/create_api_key.py --project-id <uuid> --name admin --roles admin
    python scripts/create_api_key.py --project-id <uuid> --name ci-agent --roles agent,operator
"""
from __future__ import annotations

import argparse
import sys
import uuid

# Ensure the project root is importable
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from app.auth import VALID_ROLES, hash_api_key  # noqa: E402
from app.db import init_db  # noqa: E402
from app.store import STORE  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Tascade API key")
    parser.add_argument("--project-id", required=True, help="Project UUID to scope the key to")
    parser.add_argument("--name", required=True, help="Human-readable key name")
    parser.add_argument(
        "--roles",
        required=True,
        help=f"Comma-separated role scopes ({', '.join(sorted(VALID_ROLES))})",
    )
    args = parser.parse_args()

    role_scopes = [r.strip() for r in args.roles.split(",") if r.strip()]
    invalid = set(role_scopes) - VALID_ROLES
    if invalid:
        print(f"ERROR: Invalid roles: {sorted(invalid)}", file=sys.stderr)
        print(f"Valid roles: {sorted(VALID_ROLES)}", file=sys.stderr)
        sys.exit(1)

    init_db()

    raw_key = f"tsk_{uuid.uuid4().hex}"
    key_hash = hash_api_key(raw_key)

    record = STORE.create_api_key(
        project_id=args.project_id,
        name=args.name,
        role_scopes=role_scopes,
        created_by="bootstrap-script",
        key_hash=key_hash,
    )

    print(f"API Key created successfully!")
    print(f"  ID:       {record['id']}")
    print(f"  Name:     {record['name']}")
    print(f"  Project:  {record['project_id']}")
    print(f"  Roles:    {record['role_scopes']}")
    print(f"  Raw Key:  {raw_key}")
    print()
    print("IMPORTANT: Save this key now — it cannot be retrieved again.")


if __name__ == "__main__":
    main()
