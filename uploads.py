import uuid
from pathlib import Path

from fastapi import UploadFile

UPLOAD_DIR = Path("static/uploads")
MAX_BYTES = 3 * 1024 * 1024


def _extension(datos: bytes):
    """Detecta el formato por el contenido real, no por el nombre del archivo."""
    if datos.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if datos.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return "webp"
    return None


async def guardar_imagen(archivo: UploadFile) -> str:
    datos = await archivo.read(MAX_BYTES + 1)
    if not datos:
        raise ValueError("Elige un archivo.")
    if len(datos) > MAX_BYTES:
        raise ValueError("La imagen no debe superar 3 MB.")
    ext = _extension(datos)
    if not ext:
        raise ValueError("Formato no válido. Usa JPG, PNG o WEBP.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    nombre = f"{uuid.uuid4().hex}.{ext}"
    (UPLOAD_DIR / nombre).write_bytes(datos)
    return f"/static/uploads/{nombre}"


def borrar_imagen(ruta: str | None):
    if ruta and ruta.startswith("/static/uploads/"):
        (UPLOAD_DIR / Path(ruta).name).unlink(missing_ok=True)