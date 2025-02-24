from flask import Flask
from flask_compress import Compress 
from flask_caching import Cache
from flask_cors import CORS
from log_config import logger
import firebase_admin
from firebase_admin import credentials, firestore, auth

if not firebase_admin._apps:  # Evitar inicializar Firebase más de una vez
    cred = credentials.Certificate("serviceFirebaseConfig.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# 🔥 Configurar caché en memoria
cache = Cache(config={"CACHE_TYPE": "simple", "CACHE_DEFAULT_TIMEOUT": 300})

app = Flask(__name__)
cache.init_app(app)  # Inicializar caché en Flask
CORS(app)
Compress(app)

# 🔥 Guardar Firestore, Auth y Cache en la configuración de Flask
app.config["db"] = db
app.config["auth"] = auth
app.config["cache"] = cache  # 🔥 Agregado para evitar KeyError en chat.py

# Importación de blueprints
from routes.chat import chat_bp
from routes.saldo import saldo_bp

# 🔥 Registrar rutas después de configurar `app`
app.register_blueprint(chat_bp)
app.register_blueprint(saldo_bp)

if __name__ == "__main__":
    logger.info("Servidor Flask iniciado en http://127.0.0.1:5000")
    app.run(port=5000, debug=True)
