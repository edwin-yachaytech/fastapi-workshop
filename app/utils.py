from datetime import datetime, timezone


def utcnow() -> datetime:
    """Fecha/hora UTC *sin* zona horaria (MySQL DATETIME no guarda tzinfo)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
