# backend/app/ai/validator.py

from app.core.schemas import TriageResult

VALID_LABELS = {
    1: "immediate",
    2: "high",
    3: "medium",
    4: "low",
    5: "very_low",
}


def validate_triage_output(raw: dict | None) -> TriageResult | None:
    """
    Limpia y valida el output en crudo del LLM antes de que toque la DB.
    Devuelve NOne si el output no es usable - el usuario debe de manejar ese caso.
    """
    if not raw or not isinstance(raw, dict):
        return None

    # prioridad
    priority = raw.get("priority")
    if not isinstance(priority, int) or priority not in range(1, 6):
        return None

    #  etiqueta
    label = raw.get("label", "").strip().lower()
    expected_label = VALID_LABELS[priority]
    if label != expected_label:
        # Model returned mismatched label — trust priority, fix the label
        label = expected_label

    #  reason 
    reason = raw.get("reason", "").strip()
    if not reason or len(reason) > 300:
        reason = "No reason provided."

    # red_flags 
    red_flags = raw.get("red_flags", [])
    if not isinstance(red_flags, list):
        red_flags = []
    red_flags = [
        str(f).strip() for f in red_flags
        if f and len(str(f).strip()) <= 100
    ][:10]  # cap at 10 items

    # confianza 
    confidence = raw.get("confidence", 0.5)
    try:
        confidence = float(confidence)
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.5

    return TriageResult(
        priority=priority,
        label=label,
        reason=reason,
        red_flags=red_flags,
        confidence=confidence,
    )
