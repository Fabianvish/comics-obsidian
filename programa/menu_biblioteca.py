"""Menú «Mi biblioteca»: quitar eventos o cómics y traer los cambios del catálogo (ver usa listados)."""

import xml.etree.ElementTree as ET

from .catalogo import cargar_catalogo, leer_lista_del_catalogo
from .config import guardar_config
from .generador import generar
from .listas import (
    archivos_de_eventos,
    claves_de_numeros_cbl,
    es_evento_propio,
    leer_cbl,
    nombre_original_del_evento,
    nombre_sin_orden,
    renumerar_archivos_de_eventos,
)
from .texto import (
    interpretar_posiciones,
    nombre_de_archivo_evento,
    normalizar_nombre_comic,
    normalizar_numero,
    titulo_con_anio,
)
from .ui import confirmar, elegir, paginar


def quitar_evento_o_comic(config):
    actuales = archivos_de_eventos()
    seguidos = config.get("seguidos", [])
    opciones = [("e", archivo) for archivo in actuales] + [("c", seguido) for seguido in seguidos]
    if not opciones:
        print("No hay nada que quitar.")
        return

    def describir(opcion):
        tipo, elemento = opcion
        if tipo == "e":
            return "[Evento] " + nombre_sin_orden(elemento)
        return "[Cómic]  " + titulo_con_anio(elemento["comic"], elemento["anio_comic"])

    elegido = elegir(opciones, describir, "¿Cuál se quita?")
    if not elegido:
        return
    tipo, elemento = elegido
    if tipo == "e":
        if es_evento_propio(elemento) and not confirmar(
            "⚠️ Este es un evento propio: al quitarlo se borra su lista "
            "(solo quedaría en los respaldos). ¿Confirmar? (s/n): "
        ):
            return
        actuales.remove(elemento)
        elemento.unlink()
        renumerar_archivos_de_eventos(actuales)
        print(
            "🗑️  Evento quitado (su nota se mueve a 'Archivadas'). Sus cómics se mantienen; "
            "para quitarlos también, usar esta misma opción."
        )
    else:
        # los números que son parte de un evento no se pueden quitar mientras el evento siga
        en_eventos = set()
        for archivo in actuales:
            for ejemplar in leer_cbl(archivo)[2]:
                if (
                    normalizar_nombre_comic(ejemplar["comic"]) == normalizar_nombre_comic(elemento["comic"])
                    and ejemplar["anio_comic"] == elemento["anio_comic"]
                ):
                    en_eventos.add(normalizar_numero(ejemplar["numero"]))
        quedan = [numero for numero in elemento["numeros"] if normalizar_numero(numero) in en_eventos]
        if quedan:
            elemento["numeros"] = quedan
            print(
                f"✂️  Se quitaron los números que no son de ningún evento. Se mantienen {len(quedan)} porque "
                "forman parte de un evento; para quitarlos, hay que quitar ese evento."
            )
        else:
            seguidos.remove(elemento)
            print("🗑️  Cómic quitado (su nota se mueve a 'Archivadas').")
        config["seguidos"] = seguidos
        guardar_config(config)
    generar(config)


def revisar_cambios_eventos(config):
    """Compara los eventos guardados con la versión actual del catálogo y permite actualizarlos."""
    catalogo = cargar_catalogo()
    if not catalogo:
        return
    cambios = []
    for archivo in archivos_de_eventos():
        if es_evento_propio(archivo):
            continue
        nombre = nombre_de_archivo_evento(nombre_original_del_evento(archivo))
        candidatos = [lista_catalogo for lista_catalogo in catalogo["listas"] if lista_catalogo["nombre"] == nombre]
        if len(candidatos) != 1:
            continue
        contenido_catalogo = leer_lista_del_catalogo(candidatos[0]["ruta"])
        claves_catalogo, claves_guardadas = claves_de_numeros_cbl(
            ET.fromstring(contenido_catalogo)
        ), claves_de_numeros_cbl(ET.parse(archivo).getroot())
        if claves_catalogo == claves_guardadas:
            continue
        agregados, quitados = [
            clave_ejemplar for clave_ejemplar in claves_catalogo if clave_ejemplar not in set(claves_guardadas)
        ], [clave_ejemplar for clave_ejemplar in claves_guardadas if clave_ejemplar not in set(claves_catalogo)]
        partes = (
            ([f"{len(agregados)} número(s) nuevo(s)"] if agregados else [])
            + ([f"{len(quitados)} que ya no está(n)"] if quitados else [])
            + (["cambió el orden"] if not agregados and not quitados else [])
        )
        cambios.append((archivo, contenido_catalogo, nombre, ", ".join(partes)))
    if not cambios:
        print("✅ Los eventos están al día con el catálogo.")
        return
    print("\nEventos que cambiaron en el catálogo (el progreso no se pierde: lo leído se guarda por número):")
    while True:
        respuesta = paginar(
            cambios, lambda cambio: f"{cambio[2]}: {cambio[3]}", "¿Cuáles se actualizan? (ej: 1,3  o  todos)"
        ).lower()
        elegidos = (
            list(range(1, len(cambios) + 1)) if respuesta == "todos" else interpretar_posiciones(respuesta, len(cambios))
        )
        if elegidos:
            break
        print(f"❌ Escribir números de la lista (1 a {len(cambios)}) o «todos».")
    for j in elegidos:
        cambios[j - 1][0].write_bytes(cambios[j - 1][1])
    print(f"📥 Se actualizaron {len(elegidos)} evento(s).")
    generar(config)
