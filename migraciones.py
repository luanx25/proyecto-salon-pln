from sqlalchemy import inspect, text

from database import engine


def asegurar_columnas():
    columnas = {c["name"] for c in inspect(engine).get_columns("citas")}
    if "google_event_id" not in columnas:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE citas ADD COLUMN google_event_id VARCHAR"))