from pathlib import Path
import re

import pytest


COMPOSE_FILE = Path(__file__).parents[1] / "compose.yaml"


@pytest.mark.parametrize("service_name", ["qdrant", "clickhouse", "redis"])
def test_stateful_services_wait_for_environment_validation(service_name: str) -> None:
    compose = COMPOSE_FILE.read_text()
    service = re.search(
        rf"^  {service_name}:\n(.*?)(?=^  \S|\Z)", compose, re.MULTILINE | re.DOTALL
    )

    assert service is not None
    assert "depends_on:\n      validate-env:\n        condition: service_completed_successfully" in service.group(1)


@pytest.mark.parametrize(
    ("variable", "default"),
    [
        ("CHUNK_SIZE_TOKENS", "400"),
        ("CHUNK_OVERLAP_TOKENS", "50"),
        ("OCR_LANGUAGES", "eng+vie"),
        ("OCR_DPI", "300"),
    ],
)
def test_worker_passes_ingestion_settings(variable: str, default: str) -> None:
    compose = COMPOSE_FILE.read_text()
    worker = re.search(
        r"^  worker:\n(.*?)(?=^  \S|\Z)", compose, re.MULTILINE | re.DOTALL
    )

    assert worker is not None
    assert f"{variable}: ${{{variable}:-{default}}}" in worker.group(1)
