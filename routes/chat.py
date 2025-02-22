from flask import Blueprint, request, jsonify
import openai
import google.generativeai as genai
from skyfield.api import load
from models.database import SessionLocal
from models.models import Consulta, CacheConsulta
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

        posiciones = {}
        for planeta, obj in planetas.items():
            lat, lon, dist = obj.at(t).ecliptic_latlon()
            posiciones[planeta] = round(lon.degrees, 2)

        logger.info(f"Tránsitos planetarios obtenidos: {posiciones}")
        return posiciones

    except Exception as e:
        logger.error(f"Error en obtener_transitos_skyfield: {e}")
        return {}


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
    usuario = datos.get("usuario", "Anónimo")

    if not mensaje_usuario:
        logger.warning("Solicitud sin mensaje recibido")
        return jsonify({"error": "Mensaje vacío"}), 400

    db = SessionLocal()

    # Verificar si la consulta ya existe en caché
    consulta_cache = db.query(CacheConsulta).filter(CacheConsulta.pregunta == mensaje_usuario).first()
    if consulta_cache:
        logger.info("Respuesta obtenida desde caché")
        respuesta_texto = consulta_cache.respuesta
        db.close()
        return jsonify({"respuesta": respuesta_texto})

    # Determinar cuántos tokens necesita la respuesta
    def calcular_max_tokens(mensaje):
        longitud = len(mensaje.split())
        if longitud < 10:
            return 200
        elif longitud < 30:
            return 400
        else:
            return 600

    max_tokens = calcular_max_tokens(mensaje_usuario)

    # Obtener tránsitos planetarios
    transitos = obtener_transitos_skyfield()
    transitos_str = "\n".join([f"{planeta}: {grados}°" for planeta, grados in transitos.items()])

    prompt = f"""
    Eres un astrólogo experto. Basado en estos tránsitos planetarios actuales:
    {transitos_str}

    Responde la consulta del usuario con precisión y dentro del límite de tokens disponibles ({max_tokens} tokens). 
    Si el espacio es limitado, da la respuesta más clara y resumida posible sin cortar información importante.
    Consulta del usuario: {mensaje_usuario}
    """

    try:
        logger.info("Enviando consulta a OpenAI...")
        respuesta = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens
        )

        respuesta_texto = respuesta.choices[0].message.content
        logger.info("Respuesta generada con éxito desde OpenAI")

        # Si la respuesta fue cortada, generar continuación
        if respuesta.choices[0].finish_reason == "length":
            logger.warning("La respuesta fue cortada, generando continuación...")
            respuesta_texto = continuar_respuesta(prompt, respuesta_texto)

    except openai.RateLimitError:
        logger.warning("Límite de OpenAI alcanzado, usando Google Gemini")
        respuesta_texto = genai.chat(messages=[{"role": "user", "content": prompt}]).last

    except Exception as e:
        logger.error(f"Error en la consulta a OpenAI: {e}")
        respuesta_texto = "Hubo un error al procesar tu consulta."

    nueva_cache = CacheConsulta(pregunta=mensaje_usuario, respuesta=respuesta_texto)
    db.add(nueva_cache)

    nueva_consulta = Consulta(usuario=usuario, mensaje=mensaje_usuario, respuesta=respuesta_texto)
    db.add(nueva_consulta)

    db.commit()
    db.close()
    
    logger.info(f"Respuesta enviada al usuario: {usuario}")

    return jsonify({"respuesta": respuesta_texto})
