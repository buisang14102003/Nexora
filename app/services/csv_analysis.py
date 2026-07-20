"""Restricted, reproducible CSV calculations without generated code or SQL."""

from __future__ import annotations

from io import BytesIO
from typing import Literal
from uuid import UUID

import pandas as pd
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Document, DocumentStatus
from app.services.storage import get_minio_client


class InvalidCsvOperation(ValueError):
    pass


class CsvSourceNotFound(ValueError):
    pass


class Filter(BaseModel):
    column: str = Field(min_length=1, max_length=255)
    operator: Literal["eq", "ne", "lt", "lte", "gt", "gte", "contains"]
    value: str | int | float


class Aggregation(BaseModel):
    column: str = Field(min_length=1, max_length=255)
    function: Literal["sum", "mean", "count", "min", "max"]


class CsvOperation(BaseModel):
    filters: list[Filter] = Field(default_factory=list, max_length=20)
    group_by: list[str] = Field(default_factory=list, max_length=10)
    aggregations: list[Aggregation] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def operation_has_unique_output_names(self) -> "CsvOperation":
        names = [f"{item.function}_{item.column}" for item in self.aggregations]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate aggregations are not allowed")
        if len(self.group_by) != len(set(self.group_by)):
            raise ValueError("Duplicate group_by columns are not allowed")
        return self


class CsvEvidence(BaseModel):
    source_name: str
    columns: list[str]
    filters: list[dict[str, str | int | float]]
    row_range: str | None
    row_count: int


class CsvResult(BaseModel):
    values: list[dict[str, str | int | float | None]]
    evidence: CsvEvidence


def run_csv_operation(
    document_id: UUID,
    workspace_id: UUID,
    operation: CsvOperation,
    *,
    session: Session | None = None,
) -> CsvResult:
    """Run only a validated aggregation against one ready CSV in one workspace."""

    owns_session = session is None
    if session is None:
        from app.db.session import SessionLocal

        session = SessionLocal()
    try:
        document = session.get(Document, document_id)
        if (
            document is None
            or document.workspace_id != workspace_id
            or document.source_type != "csv"
            or document.status != DocumentStatus.READY
        ):
            raise CsvSourceNotFound("CSV document not found")
        schema = document.csv_schema or {}
        _validate_columns(operation, schema)
        dataframe = _read_csv(document, _required_columns(operation))
        filtered = _apply_filters(dataframe, operation.filters)
        values = _aggregate(filtered, operation)
        return CsvResult(
            values=values,
            evidence=CsvEvidence(
                source_name=document.original_filename,
                columns=_required_columns(operation),
                filters=[item.model_dump() for item in operation.filters],
                row_range=_row_range(filtered),
                row_count=len(filtered.index),
            ),
        )
    finally:
        if owns_session:
            session.close()


def _validate_columns(operation: CsvOperation, schema: dict[str, str]) -> None:
    requested = _required_columns(operation)
    unknown = [column for column in requested if column not in schema]
    if unknown:
        raise InvalidCsvOperation("Unknown CSV column")


def _required_columns(operation: CsvOperation) -> list[str]:
    columns = [item.column for item in operation.filters]
    columns.extend(operation.group_by)
    columns.extend(item.column for item in operation.aggregations)
    return list(dict.fromkeys(columns))


def _read_csv(document: Document, columns: list[str]) -> pd.DataFrame:
    response = get_minio_client().get_object(get_settings().minio_bucket, document.object_key)
    try:
        contents = response.read()
    finally:
        response.close()
        response.release_conn()
    try:
        return pd.read_csv(BytesIO(contents), usecols=columns or None)
    except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as error:
        raise InvalidCsvOperation("CSV cannot be analyzed safely") from error


def _apply_filters(dataframe: pd.DataFrame, filters: list[Filter]) -> pd.DataFrame:
    selected = dataframe
    for item in filters:
        series = selected[item.column]
        value = _coerce_value(series, item.value)
        if item.operator == "contains":
            mask = series.astype("string").str.contains(str(item.value), regex=False, na=False)
        elif item.operator == "eq":
            mask = series == value
        elif item.operator == "ne":
            mask = series != value
        elif item.operator == "lt":
            mask = series < value
        elif item.operator == "lte":
            mask = series <= value
        elif item.operator == "gt":
            mask = series > value
        else:
            mask = series >= value
        selected = selected.loc[mask]
    return selected


def _coerce_value(series: pd.Series, value: str | int | float) -> str | int | float:
    if pd.api.types.is_numeric_dtype(series):
        try:
            return float(value)
        except (TypeError, ValueError) as error:
            raise InvalidCsvOperation("Filter value must be numeric") from error
    return str(value)


def _aggregate(dataframe: pd.DataFrame, operation: CsvOperation) -> list[dict[str, str | int | float | None]]:
    if not operation.aggregations:
        if operation.group_by:
            return [
                {**_record_key(key, operation.group_by), "row_count": int(len(group.index))}
                for key, group in dataframe.groupby(operation.group_by, dropna=False, sort=True)
            ]
        return [{"row_count": int(len(dataframe.index))}]

    groups = (
        dataframe.groupby(operation.group_by, dropna=False, sort=True)
        if operation.group_by
        else [((), dataframe)]
    )
    values: list[dict[str, str | int | float | None]] = []
    for key, group in groups:
        record = _record_key(key, operation.group_by)
        for aggregation in operation.aggregations:
            series = group[aggregation.column]
            if aggregation.function in {"sum", "mean"} and not pd.api.types.is_numeric_dtype(series):
                raise InvalidCsvOperation("sum and mean require numeric columns")
            result = getattr(series, aggregation.function)()
            record[f"{aggregation.function}_{aggregation.column}"] = _json_scalar(result)
        values.append(record)
    return values


def _record_key(key: object, columns: list[str]) -> dict[str, str | int | float | None]:
    if not columns:
        return {}
    values = key if isinstance(key, tuple) else (key,)
    return {column: _json_scalar(value) for column, value in zip(columns, values, strict=True)}


def _json_scalar(value: object) -> str | int | float | None:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()  # numpy scalar to built-in type
    if isinstance(value, (str, int, float)):
        return value
    return str(value)


def _row_range(dataframe: pd.DataFrame) -> str | None:
    if dataframe.empty:
        return None
    return f"{int(dataframe.index.min()) + 2}-{int(dataframe.index.max()) + 2}"
