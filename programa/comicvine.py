"""Cliente de la API de Comic Vine (con caché local)."""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

from .rutas import guardar_json, leer_json, RUTAS
from .constantes import PAUSA_ENTRE_PETICIONES, PETICIONES_POR_HORA, URL_API
from .errores import ErrorAPI, LimiteAPI
from .texto import clave_de_comic


def cache_personajes():
    cache = leer_json(RUTAS.estado_dir / "personajes_cache.json", {})
    cache.setdefault("numeros", {})  # id de Comic Vine del número -> [[id del personaje, nombre], ...]
    cache.setdefault("peticiones", [])  # cuándo hicimos cada petición (para respetar las 200 por hora)
    return cache


def guardar_cache_personajes(cache):
    cache["peticiones"] = [
        marca_de_tiempo for marca_de_tiempo in cache["peticiones"] if time.time() - marca_de_tiempo < 3600
    ]
    guardar_json(RUTAS.estado_dir / "personajes_cache.json", cache)


def consultar_numero(config, id_cv, cache):
    """Personajes de un número (id de Comic Vine). Busca primero en lo guardado y recién después en la API."""
    if id_cv in cache["numeros"]:
        return cache["numeros"][id_cv]
    ahora = time.time()
    cache["peticiones"] = [marca_de_tiempo for marca_de_tiempo in cache["peticiones"] if ahora - marca_de_tiempo < 3600]
    if len(cache["peticiones"]) >= PETICIONES_POR_HORA:
        espera = int((cache["peticiones"][0] + 3600 - ahora) / 60) + 1
        raise LimiteAPI(
            f"Se alcanzó el límite de peticiones por hora de Comic Vine. Se puede reintentar en unos {espera} minutos."
        )
    url = f"{URL_API}/issue/4000-{id_cv}/?" + urllib.parse.urlencode(
        {"api_key": config["clave_api"], "format": "json", "field_list": "id,character_credits"}
    )
    peticion = urllib.request.Request(url, headers={"User-Agent": "comics-obsidian"})
    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta_http:
            respuesta_json = json.loads(respuesta_http.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code in (420, 429):
            raise LimiteAPI("Comic Vine pidió esperar (demasiadas peticiones). Se puede reintentar más tarde.")
        if error.code in (401, 403):
            raise ErrorAPI("Comic Vine rechazó la clave. Revisarla en «Personajes → Clave de la API de Comic Vine».")
        raise
    cache["peticiones"].append(time.time())
    codigo = respuesta_json.get("status_code")
    if codigo == 1:
        personajes = [
            [str(credito.get("id")), credito.get("name") or ""]
            for credito in (respuesta_json.get("results") or {}).get("character_credits") or []
            if credito.get("name")
        ]
    elif codigo == 100:
        raise ErrorAPI("La clave de la API no es válida. Revisarla en «Personajes → Clave de la API de Comic Vine».")
    elif codigo == 101:
        personajes = []  # ese número no existe en Comic Vine: no vale la pena volver a pedirlo
    elif codigo == 107:
        raise LimiteAPI("Comic Vine indica que se superó el límite por hora. Se puede reintentar más tarde.")
    else:
        raise ErrorAPI(f"Comic Vine respondió con un error: {respuesta_json.get('error') or codigo}")
    cache["numeros"][id_cv] = personajes
    time.sleep(PAUSA_ENTRE_PETICIONES)
    return personajes


def id_cv_de_ejemplar(ejemplar, catalogo):
    """Id de Comic Vine de un número; usa el de la lista y, si no lo trae, el del catálogo."""
    id_cv = ejemplar.get("id_cv")
    if not id_cv and catalogo:
        titulo_catalogo = catalogo["titulos"].get(
            clave_de_comic(ejemplar["comic"], ejemplar["anio_comic"])
        )
        id_cv = (titulo_catalogo or {}).get("id_cv", {}).get(str(ejemplar["numero"]))
    return id_cv


def ids_de_comic_vine(ejemplares, catalogo):
    """Ids de Comic Vine de una lista de números, sin repetir."""
    ids_cv = []
    for ejemplar in ejemplares:
        id_cv = id_cv_de_ejemplar(ejemplar, catalogo)
        if id_cv and id_cv not in ids_cv:
            ids_cv.append(id_cv)
    return ids_cv


def contar_personajes(config, ids_cv, cache, mostrar=True):
    """Cuenta en cuántos números aparece cada personaje. Guarda lo consultado aunque se interrumpa."""
    cuenta, nombres = defaultdict(int), {}
    pendientes = [id_cv for id_cv in ids_cv if id_cv not in cache["numeros"]]
    hechos = 0
    try:
        for id_cv in ids_cv:
            es_nuevo = id_cv not in cache["numeros"]
            for id_personaje, nombre in consultar_numero(config, id_cv, cache):
                cuenta[id_personaje] += 1
                nombres[id_personaje] = nombre
            if es_nuevo:
                hechos += 1
                if mostrar and (hechos % 10 == 0 or hechos == len(pendientes)):
                    print(f"   consultados {hechos} de {len(pendientes)}...")
                if hechos % 10 == 0:
                    guardar_cache_personajes(cache)
    finally:
        guardar_cache_personajes(cache)
    return cuenta, nombres
