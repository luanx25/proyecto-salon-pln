import getpass

from database import Base, engine, SessionLocal
from models import Usuario
from security import hashear_password


def main():
    Base.metadata.create_all(bind=engine)

    email = input("Correo del administrador: ").strip().lower()
    nombre = input("Nombre: ").strip()
    password = getpass.getpass("Contraseña (mínimo 8 caracteres): ")
    confirmacion = getpass.getpass("Repite la contraseña: ")

    if not email or "@" not in email:
        print("Correo inválido.")
        return
    if not nombre:
        print("El nombre es obligatorio.")
        return
    if len(password) < 8:
        print("La contraseña debe tener al menos 8 caracteres.")
        return
    if password != confirmacion:
        print("Las contraseñas no coinciden.")
        return

    try:
        password_hash = hashear_password(password)
    except ValueError as e:
        print(e)
        return

    with SessionLocal() as db:
        if db.query(Usuario).filter(Usuario.email == email).first():
            print("Ya existe un usuario con ese correo.")
            return
        db.add(Usuario(email=email, nombre=nombre, password_hash=password_hash))
        db.commit()

    print(f"Administrador '{email}' creado correctamente.")


if __name__ == "__main__":
    main()