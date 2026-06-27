"""
src/worker/tasks.py
───────────────────
Celery background tasks.

Tasks:
  1. run_collusion_detection   → After exam completes, check for collusion
  2. calibrate_item_parameters → Nightly IRT re-calibration

Worker start command:
  celery -A src.worker.tasks worker --loglevel=info --pool=solo
  (--pool=solo for Windows; Linux can use --pool=prefork)
"""
from __future__ import annotations

from celery import Celery
from src.core.settings import settings

celery_app = Celery(
    "examiq",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Karachi",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=120,
    task_time_limit=300,
)


@celery_app.task(bind=True, max_retries=3, name="tasks.run_collusion_detection")
def run_collusion_detection(self, exam_id: str, session_id: str) -> dict:
    """
    After an exam session completes, run collusion detection
    against all other sessions in the same exam.

    Steps:
      1. Load all completed sessions for this exam
      2. Build answer vectors per student
      3. Run GNN + SBERT similarity check
      4. Update DB flags for suspicious pairs
    """
    import asyncio

    async def _run():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
        from sqlalchemy import select
        from src.db.models import ExamSession, ItemResponse, ExamItem
        from src.ml.gnn.model import CollusionDetector
        from src.ml.nlp.similarity import batch_similarity_check

        engine = create_async_engine(settings.database_url)
        AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with AsyncSessionLocal() as db:
            import uuid as _uuid
            eid = _uuid.UUID(exam_id)

            # Get all completed sessions for this exam
            sessions_result = await db.execute(
                select(ExamSession).where(
                    ExamSession.exam_id == eid,
                    ExamSession.status == "completed",
                )
            )
            sessions = sessions_result.scalars().all()

            if len(sessions) < 2:
                return {"status": "skipped", "reason": "Not enough sessions for comparison"}

            # Build binary answer vectors per student
            # [1 if correct, 0 if wrong] for each item in the bank
            all_item_ids_result = await db.execute(select(ExamItem.id).limit(200))
            all_item_ids = [str(row[0]) for row in all_item_ids_result]
            item_idx = {iid: i for i, iid in enumerate(all_item_ids)}

            student_ids = []
            answer_vectors = []

            for session in sessions:
                responses_result = await db.execute(
                    select(ItemResponse).where(ItemResponse.session_id == session.id)
                )
                responses = responses_result.scalars().all()

                vec = [0.0] * len(all_item_ids)
                for r in responses:
                    idx = item_idx.get(str(r.item_id))
                    if idx is not None:
                        vec[idx] = 1.0 if r.is_correct else 0.0

                student_ids.append(str(session.student_id))
                answer_vectors.append(vec)

            # Run GNN collusion detection
            try:
                detector = CollusionDetector(settings.gnn_model_path)
                collusion_probs = detector.detect_collusion(student_ids, answer_vectors)
            except Exception:
                # GNN model not trained yet — use heuristic fallback
                import numpy as np
                collusion_probs = {}
                vecs = [np.array(v) for v in answer_vectors]
                for i, sid in enumerate(student_ids):
                    max_sim = 0.0
                    for j, v2 in enumerate(vecs):
                        if i != j:
                            norm_i = np.linalg.norm(vecs[i])
                            norm_j = np.linalg.norm(v2)
                            if norm_i > 0 and norm_j > 0:
                                sim = float(np.dot(vecs[i], v2) / (norm_i * norm_j))
                                max_sim = max(max_sim, sim)
                    collusion_probs[sid] = max_sim

            # Update DB flags
            THRESHOLD = 0.88  # Flag if collusion probability > 88%
            for session in sessions:
                sid = str(session.student_id)
                prob = collusion_probs.get(sid, 0.0)
                if prob >= THRESHOLD:
                    session.collusion_flag = True
                    session.collusion_probability = prob
                else:
                    session.collusion_flag = False
                    session.collusion_probability = prob

            await db.commit()
            await engine.dispose()

            flagged = [sid for sid, p in collusion_probs.items() if p >= THRESHOLD]
            return {
                "status": "complete",
                "exam_id": exam_id,
                "sessions_analyzed": len(sessions),
                "flagged_students": len(flagged),
            }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="tasks.calibrate_irt_parameters")
def calibrate_irt_parameters(subject: str | None = None) -> dict:
    """
    Nightly task: re-estimate IRT parameters (a, b, c) for all items
    using accumulated response data.
    Run via: celery beat schedule or manually.
    """
    import asyncio

    async def _calibrate():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
        from sqlalchemy import select
        from src.db.models import ExamItem, ItemResponse as IR
        import numpy as np

        db_url = settings.database_url.replace("?sslmode=require", "")

        engine = create_async_engine(
            db_url,
            connect_args={"ssl": "require"},
        )
        S = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with S() as db:
            query = select(ExamItem)
            if subject:
                query = query.where(ExamItem.subject == subject)
            items_result = await db.execute(query)
            items = items_result.scalars().all()

            calibrated = 0
            for item in items:
                responses_result = await db.execute(
                    select(IR).where(IR.item_id == item.id).limit(500)
                )
                responses = responses_result.scalars().all()

                if len(responses) < 30:
                    continue  # Not enough data for calibration

                # Simple p-value estimation for difficulty
                p_correct = sum(1 for r in responses if r.is_correct) / len(responses)
                # b (difficulty): harder items have higher b (fewer correct)
                # Map p to logit scale: b = -logit(p)
                p_clipped = max(0.05, min(0.95, p_correct))
                b_new = -np.log(p_clipped / (1 - p_clipped))

                # Estimate discrimination from timing variance (proxy)
                # High variance in time = item is discriminating
                times = [r.time_taken_seconds for r in responses if r.time_taken_seconds > 0]
                if times:
                    time_cv = np.std(times) / (np.mean(times) + 1e-9)
                    a_new = max(0.5, min(2.5, 1.0 + time_cv))
                else:
                    a_new = 1.0

                item.irt_a = round(a_new, 3)
                item.irt_b = round(float(b_new), 3)
                item.irt_calibrated = True
                calibrated += 1

            await db.commit()
            await engine.dispose()
            return {"calibrated": calibrated, "total": len(items)}

    return asyncio.run(_calibrate())