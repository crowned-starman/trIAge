# backend/app/api/triage.py

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.core.schemas import PatientInput, TriageResponse
from app.core.exceptions import TriageException
from app.ai.classifier import classify_patient
from app.ai.validator import validate_triage_output
from app.db.session import get_db
from app.db.crud import create_patient, enqueue_patient
from app.blockchain.hasher import build_event_hash
from app.blockchain.logger import log_hash_to_chain

router = APIRouter()


@router.post("/triage", response_model=TriageResponse, status_code=201)
async def triage_patient(
    payload: PatientInput,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Clasificar la urgencia del paciete usando IA y añadirlos a la cola de espera.
    Devuelve como resultado un numero del 1 al 5 con razonamiento clinico
    """

    # 1. Clasificación AI 
    raw_result = await classify_patient(payload)

    # Vliadar + limpiar el output del LLM (no confiar en el modelo en raw JSON)
    triage_result = validate_triage_output(raw_result)
    if not triage_result:
        raise TriageException(
            status_code=502,
            message="El clasificador de IA devolvió una respuesta no valida. Por favor, intente de nuevo.",
            code="AI_INVALID_OUTPUT",
        )

    # Paciente persistente + resultado del triage
    patient = await create_patient(db, payload, triage_result)

    # Añador a la cola de prioridad
    queue_entry = await enqueue_patient(db, patient.id, triage_result.priority)

    # Construir el hash de eventos ("off chain"sin datos medicos) 
    event_hash = build_event_hash({
        "patient_id": str(patient.id),
        "priority":   triage_result.priority,
        "timestamp":  datetime.utcnow().isoformat(),
    })

    # Logear el hash a monad de forma asincronoca - no bloquear la respuesta
    background_tasks.add_task(log_hash_to_chain, event_hash)

    return TriageResponse(
        patient_id=str(patient.id),
        priority=triage_result.priority,
        label=triage_result.label,
        reason=triage_result.reason,
        red_flags=triage_result.red_flags,
        confidence=triage_result.confidence,
        queue_position=queue_entry.position,
        event_hash=event_hash,
        timestamp=datetime.utcnow(),
    )
