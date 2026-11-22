import bcrypt

MAX_BYTES = 72  # límite de bcrypt


def hashear_password(password: str) -> str:
    datos = password.encode("utf-8")
    if len(datos) > MAX_BYTES:
        raise ValueError("La contraseña no puede superar 72 bytes.")
    return bcrypt.hashpw(datos, bcrypt.gensalt()).decode("utf-8")


def verificar_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False