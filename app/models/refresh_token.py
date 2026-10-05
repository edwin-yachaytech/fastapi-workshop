from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils import utcnow


class RefreshToken(Base):
    """Sesiones: guardamos solo el HASH del refresh token (nunca el token en claro).

    Revocar una sesion = poner revoked_at. Asi el logout si invalida el token.
    """

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    remember_me = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")
