from pydantic import BaseModel, Field


class MensajeEntrada(BaseModel):
    mensaje: str = Field(min_length=1, max_length=500)
    cliente_email: str = Field(default="", max_length=120)
    cliente_telefono: str = Field(default="", max_length=30)