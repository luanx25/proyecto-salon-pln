# Proyecto Salón PLN

## Integrantes del Equipo
- [Gonzalez Garcia Luis Angel] - [@luanx25]


## Descripción del Problema

Los salones de belleza suelen gestionar sus operaciones (agendamiento de citas, pagos, atención al cliente) de manera manual o mediante herramientas dispersas, lo que genera errores, pérdida de tiempo y una experiencia deficiente para el cliente. Además, la falta de automatización en la atención de solicitudes y la ausencia de un panel de control centralizado dificultan la toma de decisiones y el crecimiento del negocio.

## Objetivo del Sistema
Desarrollar una **landing page** para la gestión integral de un salón de belleza, que permita a los clientes y administradores interactuar con el negocio de manera eficiente. El sistema integra un **módulo de Procesamiento de Lenguaje Natural (PLN)** para automatizar procesos clave como el agendamiento de citas, gestión de pagos y atención de solicitudes, mejorando la experiencia del usuario y reduciendo la carga operativa del personal.

Adicionalmente, se incluye un **módulo de administración** que permite a los propietarios del salón gestionar la aplicación de forma centralizada: controlar citas, clientes, servicios, reportes y configuraciones del sistema.

## ️ Tecnologías Utilizadas

- **Backend:** Python 3.13.9, FastAPI, Uvicorn
- **Frontend:** HTML, CSS, JavaScript, Jinja2 (templates)
- **Base de datos:** SQLite con SQLAlchemy
- **PLN:** [spaCy / NLTK / scikit-learn / transformers]
- **Validación:** Pydantic
- **Control de versiones:** Git y GitHub

## Instrucciones de Instalación y Ejecución
1. Clonar el repositorio:
   ```bash
   git clone https://github.com/luanx25/proyecto-salon-pln.git
   cd proyecto-salon-pln
2. Crear y activar el entorno virtual:
      python3 -m venv venv
   source venv/bin/activate  # En Windows usa: venv\Scripts\activate
3. Instalar las dependencias:
       pip install -r requirements.txt
4. Ejecutar el servidor:
   uvicorn main:app --reload
5. La API estará disponible en: http://localhost:8000
La documentación interactiva (Swagger) en: http://localhost:8000/docs



## Dependencias Necesarias
- fastapi
- uvicorn[standard]
- sqlalchemy
- jinja2

## Estado Actual del Proyecto
- [x] Estructura inicial del proyecto y configuración del entorno.
- [x] Modelos de base de datos y esquemas Pydantic definidos.
- [x] Landing page con templates HTML básicos.
- [ ] Módulo de PLN para agendamiento y atención automatizada en desarrollo.
- [ ] Módulo de administración (CRUD de citas, clientes, servicios).
- [ ] Integración de pagos y notificaciones.
- [ ] Pruebas unitarias y documentación final.