from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils import utcnow


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("auth_provider", "provider_user_id", name="uq_provider_identity"),
    )

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(150))
    email = Column(String(150), unique=True, index=True, nullable=False)

    # NULL para cuentas creadas solo con login social
    password_hash = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    # "local" (usuario/contrasena) o "github", etc.
    auth_provider = Column(String(30), default="local", nullable=False)
    provider_user_id = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=utcnow, nullable=False)

    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
