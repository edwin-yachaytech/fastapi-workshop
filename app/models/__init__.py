# Importar todos los modelos aqui garantiza que Base.metadata.create_all()
# conozca todas las tablas.
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.user import User  # noqa: F401
