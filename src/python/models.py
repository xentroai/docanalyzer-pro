from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import uuid
import os

# Create the database folder if it doesn't exist
if not os.path.exists("data"):
    os.makedirs("data")

# SQLite Database File
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/xentro_enterprise.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Document(Base):
    __tablename__ = 'documents'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String)
    file_path = Column(String)
    file_type = Column(String)  # PDF, JPG, PNG
    file_size = Column(Integer) # Bytes
    processed_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Analysis Results
    text_content = Column(Text)       # Raw C++ Output
    ai_summary = Column(Text)         # Short summary
    metadata_json = Column(JSON)      # Vendor, Total, Dates (The AI JSON)
    cpp_metrics = Column(JSON)        # Execution time, method used
    # ... inside class Document(Base) ...
    file_size = Column(Integer)
    file_hash = Column(String, index=True) # <--- NEW COLUMN
    processed_at = Column(DateTime, default=datetime.datetime.utcnow)
# ...

# Create Tables
Base.metadata.create_all(bind=engine)