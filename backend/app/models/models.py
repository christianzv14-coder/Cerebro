from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Enum as SqEnum, Text, UniqueConstraint
from sqlalchemy.orm import relationship
import enum
from app.database import Base

class Role(str, enum.Enum):
    TECH = "TECH"
    ADMIN = "ADMIN"

class ActivityState(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    EN_CURSO = "EN_CURSO"
    EXITOSO = "EXITOSO"
    FALLIDO = "FALLIDO"
    REPROGRAMADO = "REPROGRAMADO"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    tecnico_nombre = Column(String, nullable=False, unique=True) # MUST match Excel EXACTLY
    role = Column(SqEnum(Role), default=Role.TECH)
    is_active = Column(Boolean, default=True)

class FailureReason(Base):
    __tablename__ = "failure_reasons"

    code = Column(String, primary_key=True) # e.g., 'CLIENTE_AUSENTE'
    label = Column(String, nullable=False)
    active = Column(Boolean, default=True)

class Activity(Base):
    __tablename__ = "activities"

    ticket_id = Column(String, primary_key=True, index=True) # Unique and stable
    fecha = Column(Date, nullable=False, index=True)
    tecnico_nombre = Column(String, ForeignKey("users.tecnico_nombre"), nullable=False, index=True) 
    
    patente = Column(String, nullable=True)
    cliente = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    tipo_trabajo = Column(String, nullable=True)
    
    # New fields from Mantis
    prioridad = Column(String, nullable=True)
    accesorios = Column(String, nullable=True)
    comuna = Column(String, nullable=True)
    region = Column(String, nullable=True)
    
    estado = Column(SqEnum(ActivityState), default=ActivityState.PENDIENTE, index=True)
    
    hora_inicio = Column(DateTime, nullable=True)
    hora_fin = Column(DateTime, nullable=True)
    duracion_min = Column(Integer, nullable=True)
    
    resultado_motivo = Column(String, ForeignKey("failure_reasons.code"), nullable=True)
    observacion = Column(Text, nullable=True)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DaySignature(Base):
    __tablename__ = "day_signatures"

    id = Column(Integer, primary_key=True, index=True)
    tecnico_nombre = Column(String, ForeignKey("users.tecnico_nombre"), nullable=False)
    fecha = Column(Date, nullable=False)
    signature_ref = Column(String, nullable=False) # URL or Path
    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("tecnico_nombre", "fecha", name="_tech_date_uc"),)
