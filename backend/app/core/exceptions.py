# backend/app/core/exceptions.py

from fastapi import HTTPException


class TriageException(HTTPException):
    def __init__(self, status_code: int, message: str, code: str):
        super().__init__(status_code=status_code, detail=message)
        self.message = message
        self.code    = code


# Excepciones predefinidas

class PatientNotFoundException(TriageException):
    def __init__(self, patient_id: str):
        super().__init__(
            status_code=404,
            message=f"Patient {patient_id} not found",
            code="PATIENT_NOT_FOUND",
        )

class QueueEntryNotFoundException(TriageException):
    def __init__(self, patient_id: str):
        super().__init__(
            status_code=404,
            message=f"No queue entry found for patient {patient_id}",
            code="QUEUE_ENTRY_NOT_FOUND",
        )

class InvalidStatusTransitionException(TriageException):
    def __init__(self, from_status: str, to_status: str):
        super().__init__(
            status_code=422,
            message=f"Cannot transition from '{from_status}' to '{to_status}'",
            code="INVALID_STATUS_TRANSITION",
        )

class AIClassifierException(TriageException):
    def __init__(self):
        super().__init__(
            status_code=502,
            message="AI classifier returned an invalid response. Please retry.",
            code="AI_INVALID_OUTPUT",
        )
