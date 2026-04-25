# backend/app/api/queue.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.schemas import (
    QueueResponse,
    QueueEntryUpdate,
    QueueSummary,
)
from app.core.exceptions import TriageException
from app.db.session import get_db
from app.db.crud import (
    get_queue,
    get_queue_entry,
    update_queue_status,
    remove_from_queue,
)

router = APIRouter()


@router.get("/queue", response_model=list[QueueResponse])
async def list_queue(
    status: Optional[str] = Query(None, pattern="^(esperando|en_progreso|hecho$"),
    priority: Optional[int] = Query(None, ge=1, le=5),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Devuelve el lugar del paciente en la fila
    Ordenado por prioridad
    Se puede filtrar por estado y nivel de prioridad
    """
    entries = await get_queue(
        db,
        status=status,
        priority=priority,
        limit=limit,
    )
    return entries


@router.get("/queue/summary", response_model=QueueSummary)
async def queue_summary(db: AsyncSession = Depends(get_db)):
    """
    Devolver la info del dashboard:
    timepo de espera toral, conteo por nivel de prioridad y paciente con mas tiempo de espera
    """
    entries = await get_queue(db, status="waiting", limit=200)

    counts = {i: 0 for i in range(1, 6)}
    oldest = None

    for e in entries:
        counts[e.priority] += 1
        if oldest is None or e.enqueued_at < oldest:
            oldest = e.enqueued_at

    return QueueSummary(
        total_waiting=len(entries),
        by_priority=counts,
        oldest_waiting=oldest,
    )


@router.get("/queue/{patient_id}", response_model=QueueResponse)
async def get_queue_entry_by_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Ver la entrada de un paciente en específico
    """
    entry = await get_queue_entry(db, patient_id)
    if not entry:
        raise TriageException(
            status_code=404,
            message=f"No queue entry found for patient {patient_id}",
            code="QUEUE_ENTRY_NOT_FOUND",
        )
    return entry


@router.patch("/queue/{patient_id}", response_model=QueueResponse)
async def update_patient_status(
    patient_id: str,
    body: QueueEntryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Actualizar el estado del paciente en la fila
    Transiciones: esperando -> en_porgrso -> atendido
    Update a patient's queue status.
    Transitions: waiting -> in_progress -> done
    Used by hospital staff to advance patients through the queue.
    """
    VALID_TRANSITIONS = {
        "sperando":     ["en_progreso"],
        "en_progreso": ["hecho"],
        "hecho":        [],
    }

    entry = await get_queue_entry(db, patient_id)
    if not entry:
        raise TriageException(
            status_code=404,
            message=f"No queue entry found for patient {patient_id}",
            code="QUEUE_ENTRY_NOT_FOUND",
        )

    allowed = VALID_TRANSITIONS.get(entry.status, [])
    if body.status not in allowed:
        raise TriageException(
            status_code=422,
            message=f"No se puede avanzar de '{entry.status}' a '{body.status}'",
            code="INVALID_STATUS_TRANSITION",
        )

    updated = await update_queue_status(db, patient_id, body.status)
    return updated


@router.delete("/queue/{patient_id}", status_code=204)
async def remove_patient_from_queue(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Remover completamente el paciente de la fila.
    Uasr para cancelaciones o correcciones de datos - no para el flujo de alta normal.
    """
    entry = await get_queue_entry(db, patient_id)
    if not entry:
        raise TriageException(
            status_code=404,
            message=f"No se encontraron datos del paciente {patient_id}",
            code="QUEUE_ENTRY_NOT_FOUND",
        )

    await remove_from_queue(db, patient_id)
