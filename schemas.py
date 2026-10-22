from pydantic import BaseModel


class MensajeEntrada(BaseModel):
    mensaje: str
    cliente_email: str
    cliente_telefono: str