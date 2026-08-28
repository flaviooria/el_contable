from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class MovementType(str, Enum):
    INGRESO = "ingreso"
    GASTO = "gasto"


class MovementBase(BaseModel):
    fecha_movimiento: datetime
    concepto: str = Field(..., min_length=1)
    importe: float
    tipo: MovementType
    disponible: float


class MovementCreate(MovementBase):
    pass


class MovementResponse(MovementBase):
    id: int
    created_at: datetime
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MovementRow(BaseModel):
    fecha: str | None = None
    fecha_movimiento: datetime | None = None
    concepto: str | None = None
    movimiento: str | None = None
    importe: float | None = None
    disponible: float | None = None
    is_valid: bool = True
    validation_error: str | None = None


class UploadResponse(BaseModel):
    inserted_count: int
    skipped_count: int
    available_balance: float
    movements: list[MovementResponse]


class UploadError(BaseModel):
    detail: str
    errors: list[str] | None = None
