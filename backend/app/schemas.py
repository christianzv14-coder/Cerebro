from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime
from app.models.models import ActivityState

class Token(BaseModel):
    access_token: str
    token_type: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    tecnico_nombre: str
    role: str
    
    class Config:
        from_attributes = True

class ActivityBase(BaseModel):
    ticket_id: str
    fecha: date
    tecnico_nombre: str
    patente: Optional[str] = None
    cliente: Optional[str] = None
    direccion: Optional[str] = None
    tipo_trabajo: Optional[str] = None
    estado: ActivityState

class ActivityResponse(ActivityBase):
    hora_inicio: Optional[datetime] = None
    hora_fin: Optional[datetime] = None
    duracion_min: Optional[int] = None
    resultado_motivo: Optional[str] = None
    observacion: Optional[str] = None
    
    class Config:
         from_attributes = True

class ActivityStart(BaseModel):
    timestamp: datetime # Local timestamp from App (or empty to use server time)

class ActivityFinish(BaseModel):
    timestamp: datetime
    resultado: str # EXITOSO / FALLIDO
    motivo: Optional[str] = None
    observacion: Optional[str] = None
