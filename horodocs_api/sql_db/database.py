from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# File to allow sql db operations

SQLALCHEMY_DATABASE_URL = "sqlite:///./config_sql.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, pool_size=0, 
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for fast API. Return the database when it is ready.

    :yield: Database
    :rtype: Session object
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

