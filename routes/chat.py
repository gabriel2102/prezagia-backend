from flask import Blueprint, request, jsonify, current_app
import openai
import google.generativeai as genai
from skyfield.api import load
from config import Config
from log_config import logger

chat_bp = Blueprint("chat", __name__)

# Inicializar OpenAI y Google Gemini
openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
genai.configure(api_key=Config.GEMINI_API_KEY)

def obtener_transitos_skyfield():
    """ Obtiene la posición actual de los planetas en la eclíptica usando Skyfield. """
    try:
        logger.info("Cargando efemérides de la NASA...")
        eph = load('de421.bsp')
        ts = load.timescale()
        t = ts.now()

        planetas = {
            'Sol': eph['sun'],
            'Luna': eph['moon'],
            'Mercurio': eph['mercury'],
            'Venus': eph['venus'],
            'Marte': eph['mars'],
            'Júpiter': eph['jupiter barycenter'],
            'Saturno': eph['saturn barycenter'],
            'Urano': eph['uranus barycenter'],
            'Neptuno': eph['neptune barycenter'],
            'Plutón': eph['pluto barycenter']
        }

        posiciones = {planeta: round(obj.at(t).ecliptic_latlon()[1].degrees, 2) for planeta, obj in planetas.items()}
        logger.info(f"Tránsitos planetarios obtenidos: {posiciones}")
        return posiciones
    except Exception as e:
        logger.error(f"Error en obtener_transitos_skyfield: {e}")
        return {}

def calcular_max_tokens(mensaje):
    """ Calcula dinámicamente los tokens según la longitud de la pregunta. """
    longitud = len(mensaje.split())
    if longitud < 10:
        return 150
    elif longitud < 30:
        return 300
    return 500  # 🔥 Máximo 500 tokens para evitar costos elevados

def continuar_respuesta(prompt, respuesta_inicial):
    """ Pide a OpenAI que continúe una respuesta si se cortó. """
    nuevo_prompt = f"""
    La respuesta anterior quedó incompleta:
    "{respuesta_inicial}"

    Continúa la respuesta dentro del límite de tokens disponibles. 
    Evita repetir lo que ya has dicho y concéntrate en completar la idea.
    """
    try:
        nueva_respuesta = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": nuevo_prompt}],
            max_tokens=300  # Solo para completar lo que falta
        )
        return respuesta_inicial + " " + nueva_respuesta.choices[0].message.content
    except Exception as e:
        logger.error(f"Error al continuar la respuesta: {e}")
        return respuesta_inicial  # Retornar la respuesta parcial si falla la continuación

@chat_bp.route("/chat", methods=["POST"])
def chat():
    logger.info("Recibida solicitud en /chat")

    datos = request.json
    mensaje_usuario = datos.get("mensaje", "")
    token = request.headers.get("Authorization")

    if not token:
        return jsonify({"error": "No autenticado"}), 401

    db = current_app.config["db"]
    auth = current_app.config["auth"]
    cache = current_app.config["cache"]  # 🔥 Obtener cache correctamente

    # 🔥 Verificar usuario autenticado
    try:
        decoded_token = auth.verify_id_token(token.replace("Bearer ", ""))
        usuario = decoded_token["uid"]
        logger.info(f"Usuario autenticado: {usuario}")
    except Exception as e:
        logger.error(f"Error al verificar token: {e}")
        return jsonify({"error": "Token inválido"}), 401

    if not mensaje_usuario:
        return jsonify({"error": "Mensaje vacío"}), 400

    # 🔥 Buscar en caché (memoria y Firestore)
    cache_key = f"chat_cache_{usuario}_{mensaje_usuario}"
    respuesta_texto = cache.get(cache_key)

    if not respuesta_texto:
        consulta_cache = db.collection("usuarios").document(usuario).collection("cache_consulta").where(
            "pregunta", "==", mensaje_usuario).limit(1).stream()
        cache_existente = next(consulta_cache, None)

        if cache_existente:
            respuesta_texto = cache_existente.to_dict()["respuesta"]
            cache.set(cache_key, respuesta_texto)

    # 🔥 Si aún no hay respuesta, consultar OpenAI
    if not respuesta_texto:
        transitos = obtener_transitos_skyfield()
        transitos_str = "\n".join([f"{planeta}: {grados}°" for planeta, grados in transitos.items()])

        prompt = f"""
        Eres un astrólogo experto. Basado en estos tránsitos planetarios actuales:
        {transitos_str}

        Responde la consulta del usuario con precisión en un máximo de {calcular_max_tokens(mensaje_usuario)} tokens.
        Consulta del usuario: {mensaje_usuario}
        """

        try:
            respuesta = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=calcular_max_tokens(mensaje_usuario),
                temperature=0.7
            )

            respuesta_texto = respuesta.choices[0].message.content
            logger.info("Respuesta generada con éxito desde OpenAI")

            # Si la respuesta fue cortada, generar continuación
            if respuesta.choices[0].finish_reason == "length":
                respuesta_texto += continuar_respuesta(prompt, respuesta_texto)

        except openai.RateLimitError:
            logger.warning("Límite de OpenAI alcanzado, usando Google Gemini")
            respuesta_texto = genai.chat(messages=[{"role": "user", "content": prompt}]).last

        except Exception as e:
            logger.error(f"Error en la consulta a OpenAI: {e}")
            respuesta_texto = "Hubo un error al procesar tu consulta."

        # 🔥 Guardar respuesta en Firestore y en caché con una transacción
        batch = db.batch()
        cache_data = {"pregunta": mensaje_usuario, "respuesta": respuesta_texto}
        consulta_data = {"mensaje": mensaje_usuario, "respuesta": respuesta_texto}

        batch.set(db.collection("usuarios").document(usuario).collection("cache_consulta").document(), cache_data)
        batch.set(db.collection("usuarios").document(usuario).collection("consultas").document(), consulta_data)
        batch.commit()

        cache.set(cache_key, respuesta_texto)

    logger.info(f"Respuesta enviada al usuario: {usuario}")
    return jsonify({"respuesta": respuesta_texto})
