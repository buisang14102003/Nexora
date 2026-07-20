from io import BytesIO
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import Document, DocumentStatus


class _ObjectResponse:
    def __init__(self, contents: bytes) -> None:
        self._contents = contents

    def read(self) -> bytes:
        return self._contents

    def close(self) -> None:
        pass

    def release_conn(self) -> None:
        pass


class _Minio:
    def __init__(self, contents: bytes) -> None:
        self._contents = contents
        self.requested_keys: list[str] = []

    def get_object(self, bucket: str, key: str) -> _ObjectResponse:
        self.requested_keys.append(key)
        return _ObjectResponse(self._contents)


@pytest.fixture
def csv_document() -> tuple[Session, Document, _Minio]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    workspace_id = uuid4()
    document = Document(
        id=uuid4(),
        workspace_id=workspace_id,
        original_filename="sales.csv",
        mime_type="text/csv",
        object_key=f"{workspace_id}/sales.csv",
        source_type="csv",
        status=DocumentStatus.READY,
        csv_schema={"country": "object", "amount": "int64", "team": "object"},
        csv_row_count=3,
    )
    session = Session(engine)
    session.add(document)
    session.commit()
    minio = _Minio(b"country,amount,team\nVN,500,A\nUS,300,A\nVN,750,B\n")
    try:
        yield session, document, minio
    finally:
        session.close()
        engine.dispose()


def test_csv_sum_is_reproducible(csv_document, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import csv_analysis
    from app.services.csv_analysis import Aggregation, CsvOperation, Filter, run_csv_operation

    session, document, minio = csv_document
    monkeypatch.setattr(csv_analysis, "get_minio_client", lambda: minio)

    result = run_csv_operation(
        document.id,
        document.workspace_id,
        CsvOperation(
            filters=[Filter(column="country", operator="eq", value="VN")],
            group_by=[],
            aggregations=[Aggregation(column="amount", function="sum")],
        ),
        session=session,
    )

    assert result.values == [{"sum_amount": 1250.0}]
    assert result.evidence.source_name == "sales.csv"
    assert result.evidence.columns == ["country", "amount"]
    assert result.evidence.filters == [{"column": "country", "operator": "eq", "value": "VN"}]
    assert result.evidence.row_range == "2-4"
    assert result.evidence.row_count == 2


def test_unknown_column_is_rejected_before_object_access(
    csv_document, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services import csv_analysis
    from app.services.csv_analysis import CsvOperation, Filter, InvalidCsvOperation, run_csv_operation

    session, document, minio = csv_document
    monkeypatch.setattr(csv_analysis, "get_minio_client", lambda: minio)

    with pytest.raises(InvalidCsvOperation):
        run_csv_operation(
            document.id,
            document.workspace_id,
            CsvOperation(
                filters=[Filter(column="DROP TABLE", operator="eq", value="x")],
                group_by=[],
                aggregations=[],
            ),
            session=session,
        )

    assert minio.requested_keys == []


def test_document_from_another_workspace_is_not_loaded(csv_document, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import csv_analysis
    from app.services.csv_analysis import CsvOperation, CsvSourceNotFound, run_csv_operation

    session, document, minio = csv_document
    monkeypatch.setattr(csv_analysis, "get_minio_client", lambda: minio)

    with pytest.raises(CsvSourceNotFound):
        run_csv_operation(document.id, uuid4(), CsvOperation(filters=[], group_by=[], aggregations=[]), session=session)

    assert minio.requested_keys == []


def test_group_by_requires_an_aggregation() -> None:
    from pydantic import ValidationError

    from app.services.csv_analysis import CsvOperation

    with pytest.raises(ValidationError, match="group_by requires at least one aggregation"):
        CsvOperation(group_by=["country"], aggregations=[])
