from collections.abc import Callable
from threading import Event

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import IngestionJob
from app.services.jobs import claim_next_job, fail_job, process_claimed_job
from app.services.vector_store import QdrantVectorStore


SessionFactory = Callable[[], Session]


def run_once(
    *,
    session_factory: SessionFactory | None = None,
    vector_store: QdrantVectorStore | None = None,
) -> bool:
    if session_factory is None:
        from app.db.session import SessionLocal

        factory = SessionLocal
    else:
        factory = session_factory
    with factory() as session:
        with session.begin():
            claimed = claim_next_job(session)
            if claimed is None:
                return False
            job_id = claimed.id

    try:
        with factory() as session:
            with session.begin():
                job = session.get(IngestionJob, job_id)
                if job is None:
                    raise RuntimeError("Claimed ingestion job no longer exists")
                process_claimed_job(session, job, vector_store)
    except Exception as error:
        with factory() as session:
            with session.begin():
                job = session.get(IngestionJob, job_id)
                if job is None:
                    raise RuntimeError("Claimed ingestion job no longer exists") from error
                fail_job(session, job, error)
    return True


def main() -> None:
    shutdown = Event()
    try:
        while True:
            processed = run_once()
            if not processed and shutdown.wait(get_settings().worker_poll_seconds):
                break
    except KeyboardInterrupt:
        shutdown.set()


if __name__ == "__main__":
    main()
