# backend/app/core/schemas.py

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


# ── Input ──────────────────────────────────────────────────────────────────────

class Vitals(BaseModel):
    bp:   Optional[str]   = None  # e.g. "120/80"
    hr:   Optional[int]   = None  # latidos por minuto
    temp: Optional[float] = None  # Celsius
    spo2: Optional[int]   = None  # porcentaje 0–100

class PatientInput(BaseModel):
    age:      int        = Field(..., ge=0, le=130)
    symptoms: list[str]  = Field(..., min_length=1, max_length=20)
    vitals:   Optional[Vitals] = None

    @field_validator("symptoms")
    @classmethod
    def sanitize_symptoms(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip().lower() for s in v if s.strip()]
        if not cleaned:
            raise ValueError("At least one valid symptom is required")
        return cleaned[:20]  # hard cap


# Capa de IA

class TriageResult(BaseModel):
    priority:   int        = Field(..., ge=1, le=5)
    label:      str
    reason:     str
    red_flags:  list[str]  = []
    confidence: float      = Field(..., ge=0.0, le=1.0)


# Respuestas API

class TriageResponse(BaseModel):
    patient_id:     str
    priority:       int
    label:          str
    reason:         str
    red_flags:      list[str]
    confidence:     float
    queue_position: int
    event_hash:     str
    timestamp:      datetime

class PatientResponse(BaseModel):
    id:         UUID
    age:        int
    priority:   int
    label:      str
    confidence: float
    seen_at:    Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class PatientDetail(PatientResponse):
    symptoms:    list[str]
    reason:      str
    red_flags:   list[str]
    event_hash:  Optional[str] = None
    vitals:      Optional[Vitals] = None

    model_config = {"from_attributes": True}


# Fila

class QueueResponse(BaseModel):
    patient_id:  UUID
    priority:    int
    position:    int
    status:      str
    enqueued_at: datetime

    model_config = {"from_attributes": True}

class QueueEntryUpdate(BaseModel):
    status: str = Field(..., pattern="^(esperando|en_progreso|hecho)$")

class QueueSummary(BaseModel):
    total_waiting: int
    by_priority:   dict[int, int]  # {1: 2, 2: 5, 3: 8, ...}
    oldest_waiting: Optional[datetime] = None
