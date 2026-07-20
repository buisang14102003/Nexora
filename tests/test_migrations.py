import os
import subprocess
import sys

from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_head_creates_domain_tables(tmp_path) -> None:
    database_path = tmp_path / "migration-smoke.db"
    environment = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{database_path}",
        "JWT_SECRET": "test",
    }

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        check=False,
        cwd=".",
        env=environment,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert {"users", "workspaces", "memberships"} <= set(
        inspect(create_engine(f"sqlite:///{database_path}")).get_table_names()
    )
