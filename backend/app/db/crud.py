# backend/app/db/crud.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from datetime import datetime
from uuid import UUID

from app.db.models import Patient, QueueEntry
from app.core.schemas import PatientInput, TriageResult


# Pacientes

async def create_patient(
    db: AsyncSession,
    payload: PatientInput,
    result: TriageResult,
) -> Patient:
    patient = Patient(
        age        = payload.age,
        symptoms   = payload.symptoms,
        priority   = result.priority,
        label      = result.label,
        reason     = result.reason,
        red_flags  = result.red_flags,
        confidence = result.confidence,
        vitals_bp   = payload.vitals.bp   if payload.vitals else None,
        vitals_hr   = payload.vitals.hr   if payload.vitals else None,
        vitals_temp = payload.vitals.temp if payload.vitals else None,
        vitals_spo2 = payload.vitals.spo2 if payload.vitals else None,
    )
    db.add(patient)
    await db.flush()  # obtiene el UUID sin hacer commit todavía
    return patient


async def get_patient_by_id(
    db: AsyncSession,
    patient_id: str,
) -> Patient | None:
    result = await db.execute(
        select(Patient).where(Patient.id == UUID(patient_id))
    )
    return result.scalar_one_or_none()


async def get_all_patients(
    db: AsyncSession,
    priority: int | None = None,
    seen: bool | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Patient]:
    query = select(Patient).order_by(Patient.created_at.desc())

    if priority is not None:
        query = query.where(Patient.priority == priority)
    if seen is True:
        query = query.where(Patient.seen_at.isnot(None))
    if seen is False:
        query = query.where(Patient.seen_at.is_(None))
    if from_date:
        query = query.where(Patient.created_at >= from_date)
    if to_date:
        query = query.where(Patient.created_at <= to_date)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


async def mark_patient_seen(
    db: AsyncSession,
    patient_id: str,
) -> Patient | None:
    await db.execute(
        update(Patient)
        .where(Patient.id == UUID(patient_id))
        .values(seen_at=datetime.utcnow())
    )
    await db.flush()
    return await get_patient_by_id(db, patient_id)


async def update_patient_hash(
    db: AsyncSession,
    patient_id: str,
    event_hash: str,
) -> None:
    await db.execute(
        update(Patient)
        .where(Patient.id == UUID(patient_id))
        .values(event_hash=event_hash)
    )


# Fila

async def enqueue_patient(
    db: AsyncSession,
    patient_id: UUID,
    priority: int,
) -> QueueEntry:
    # Calcula la siguiente posición disponible
    result = await db.execute(
        select(func.count()).where(
            QueueEntry.status == "waiting"
        )
    )
    waiting_count = result.scalar_one()

    entry = QueueEntry(
        patient_id  = patient_id,
        priority    = priority,
        position    = waiting_count + 1,
        status      = "waiting",
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_queue(
    db: AsyncSession,
    status: str | None = None,
    priority: int | None = None,
    limit: int = 50,
) -> list[QueueEntry]:
    query = (
        select(QueueEntry)
        .order_by(QueueEntry.priority.asc(), QueueEntry.enqueued_at.asc())
    )

    if status:
        query = query.where(QueueEntry.status == status)
    if priority:
        query = query.where(QueueEntry.priority == priority)

    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_queue_entry(
    db: AsyncSession,
    patient_id: str,
) -> QueueEntry | None:
    result = await db.execute(
        select(QueueEntry).where(QueueEntry.patient_id == UUID(patient_id))
    )
    return result.scalar_one_or_none()


async def update_queue_status(
    db: AsyncSession,
    patient_id: str,
    status: str,
) -> QueueEntry | None:
    await db.execute(
        update(QueueEntry)
        .where(QueueEntry.patient_id == UUID(patient_id))
        .values(status=status)
    )
    await db.flush()
    return await get_queue_entry(db, patient_id)


async def remove_from_queue(
    db: AsyncSession,
    patient_id: str,
) -> None:
    await db.execute(
        delete(QueueEntry)
        .where(QueueEntry.patient_id == UUID(patient_id))
    )
