import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_env.py"


def test_validate_env_reports_blank_required_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("POSTGRES_PASSWORD=\nMINIO_ROOT_PASSWORD=ready\n")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--env-file", str(env_file)],
        capture_output=True,
        text=True,
        check=False,
        env={"POSTGRES_PASSWORD": "host-password"},
    )

    assert result.returncode == 1
    assert "DATABASE_URL, POSTGRES_PASSWORD, JWT_SECRET" in result.stderr
    assert "JWT_SECRET" in result.stderr
