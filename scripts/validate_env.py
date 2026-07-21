"""Validate the required local-runtime values before Docker services start."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REQUIRED_VARIABLES = (
    "DATABASE_URL",
    "POSTGRES_PASSWORD",
    "MINIO_ROOT_PASSWORD",
    "JWT_SECRET",
    "CHAINLIT_AUTH_SECRET",
    "LANGFUSE_POSTGRES_PASSWORD",
    "LANGFUSE_NEXTAUTH_SECRET",
    "LANGFUSE_SALT",
    "LANGFUSE_ENCRYPTION_KEY",
)


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator:
            continue
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def missing_required_variables(values: dict[str, str]) -> list[str]:
    return [name for name in REQUIRED_VARIABLES if not values.get(name, "").strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    args = parser.parse_args()

    if not args.env_file.is_file():
        print(f"Missing environment file: {args.env_file}", file=sys.stderr)
        return 1

    values = {**os.environ, **read_env_file(args.env_file)}
    missing = missing_required_variables(values)
    if missing:
        print(
            "Set non-empty values in .env before starting Docker: " + ", ".join(missing),
            file=sys.stderr,
        )
        return 1

    print("Environment validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
