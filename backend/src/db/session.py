from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.config import settings
from src.db.models.base import Base

# Create standard sync PostgreSQL engine.
# For FastF1 metadata, sync is extremely fast and simpler;
# high-frequency telemetry won't be queried natively via the ORM.
engine = create_engine(
    settings.NEON_DB_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
