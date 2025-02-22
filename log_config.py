import logging
from datetime import datetime
from models.database import SessionLocal
from models.models import Log


# Configurar el logging para que se guarde en un archivo y también se muestre en la terminal
logging.basicConfig(
    level=logging.INFO,  # Nivel de logs: DEBUG, INFO, WARNING, ERROR, CRITICAL
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("backend.log"),  # Guarda logs en un archivo
        logging.StreamHandler()  # Muestra logs en la consola
    ]
)

logger = logging.getLogger(__name__)  # Instancia global de logger

def log_to_db(level, message):
    try:
        db = SessionLocal()
        nuevo_log = Log(nivel=level, mensaje=message, fecha=datetime.utcnow())
        db.add(nuevo_log)
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Error guardando log en la base de datos: {e}")