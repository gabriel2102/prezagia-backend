from skyfield.api import load

def obtener_transitos_skyfield():
    try:
        # Cargar las efemérides de la NASA
        eph = load('de421.bsp')
        ts = load.timescale()
        t = ts.now()

        # Definir los planetas a consultar
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

        # Obtener la posición de los planetas en la eclíptica
        posiciones = {}
        for planeta, obj in planetas.items():
            lat, lon, dist = obj.at(t).ecliptic_latlon()
            posiciones[planeta] = round(lon.degrees, 2)  # Guardar solo la longitud en grados

        return posiciones

    except Exception as e:
        print(f"Error en obtener_transitos_skyfield: {e}")
        return {}
