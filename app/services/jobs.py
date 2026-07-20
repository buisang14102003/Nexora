from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import IngestionJob, IngestionJobStatus


def claim_next_job(session: Session) -> IngestionJob | None:
    job = session.scalar(
        select(IngestionJob)
        .where(IngestionJob.status == IngestionJobStatus.QUEUED)
        .order_by(IngestionJob.created_at, IngestionJob.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if job is None:
        return None

    job.status = IngestionJobStatus.PROCESSING
    job.attempts += 1
    job.claimed_at = datetime.now(timezone.utc)
    session.flush()
    return job
