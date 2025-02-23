from flask import Blueprint, jsonify
import requests
from config import Config
from log_config import logger


saldo_bp = Blueprint("saldo", __name__)

@saldo_bp.route("/saldo", methods=["GET"])
def verificar_saldo():
    try:
        headers = {"Authorization": f"Bearer {Config.OPENAI_API_KEY}"}
        response = requests.get("https://api.openai.com/v1/usage", headers=headers)
        logger.info("Saldo de OpenAI obtenido correctamente.")
        return jsonify(response.json())
    except Exception as e:
        logger.error(f"Error al obtener saldo de OpenAI: {e}")
        return jsonify({"error": "Error al obtener saldo de OpenAI"}), 500
