from flask import Flask
from flask_cors import CORS
from routes.chat import chat_bp
from routes.saldo import saldo_bp
from log_config import logger

app = Flask(__name__)
CORS(app)

# Registrar rutas
app.register_blueprint(chat_bp)
app.register_blueprint(saldo_bp)

if __name__ == "__main__":
    logger.info("Servidor Flask iniciado en http://127.0.0.1:5000")
    app.run(port=5000, debug=True)
