# backend/app/api/patients.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from app.core.schemas import PatientResponse, PatientDetail
from app.core.exceptions import TriageException
from app.db.session import get_db
from app.db.crud import (
    get_patient_by_id,
    get_all_patients,
    mark_patient_seen,
)

router = APIRouter()


@router.get("/patients", response_model=list[PatientResponse])
async def list_patients(
    priority: Optional[int] = Query(None, ge=1, le=5),
    seen: Optional[bool] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista los pacientes evaluados con opciones de filtros.
    Esto se usa en el hoistorial del dashboard y en el log de auditorias.
    """
    patients = await get_all_patients(
        db,
        priority=priority,
        seen=seen,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )
    return patients


@router.get("/patients/{patient_id}", response_model=PatientDetail)
async def get_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Devolver en detalle la info del paciente seleccionado incluyendo el resultado del triage,
    historial de cola y el evento bash del blockcahin
    """
    patient = await get_patient_by_id(db, patient_id)
    if not patient:
        raise TriageException(
            status_code=404,
            message=f"Patient {patient_id} not found",
            code="PATIENT_NOT_FOUND",
        )
    return patient


@router.patch("/patients/{patient_id}/seen", response_model=PatientResponse)
async def mark_seen(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Marcar el paciente como "visto" por un medico
    Lo graba en seen_at timestamp. Idempotent - es seguro llamarlo multiple veces
    """
    patient = await get_patient_by_id(db, patient_id)
    if not patient:
        raise TriageException(
            status_code=404,
            message=f"Patient {patient_id} not found",
            code="PACIENTE_NO_ENCONTRADO",
        )

    if patient.seen_at:
        # Already marked — return as-is, no error
        return patient

    updated = await mark_patient_seen(db, patient_id)
    return updated
