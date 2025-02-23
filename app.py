from flask import Flask
from flask_cors import CORS
from routes.chat import chat_bp
from routes.saldo import saldo_bp
from log_config import logger
import firebase_admin
from firebase_admin import credentials, firestore, auth

cred = credentials.Certificate("serviceFirebaseConfig.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)
CORS(app)

# Guardar Firestore y Auth en la configuración de Flask
app.config["db"] = db
app.config["auth"] = auth

# importación de blueprints
from routes.chat import chat_bp
from routes.saldo import saldo_bp

# Registrar rutas
app.register_blueprint(chat_bp)
app.register_blueprint(saldo_bp)

if __name__ == "__main__":
    logger.info("Servidor Flask iniciado en http://127.0.0.1:5000")
    app.run(port=5000, debug=True)
