from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Importa os modelos para que sejam registrados com a Base
from app.models import user, team, password_reset
# New models for multi-user teams, organizations, permissions, and logging
from app.models import (
    organization,
    provider,
    client,
    guest,
    organization_member,
    team_member,
    permission,
    api_access_log,
    error_log
)

