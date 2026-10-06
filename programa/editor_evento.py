"""Editor de eventos propios: ver su orden de lectura por páginas, agregar, quitar, mover, años y carpeta."""

import re

from .busqueda import elegir_comic_y_numeros
from .catalogo import cargar_catalogo
from .constantes import CARPETA_NOTAS_EVENTOS, CARPETAS_RESERVADAS, RESULTADOS_POR_PAGINA
from .generador import generar
from .listas import (
    agregar_numeros_evento,
    anios_de_evento,
    anios_indicados_a_mano,
    archivos_de_eventos,
    carpeta_de_nota,
    es_evento_propio,
    escribir_cbl,
    leer_cbl,
    nombre_original_del_evento,
    nombre_sin_orden,
    nombres_de_eventos,
)
from .teclado import Cancelado, pedir_texto
from .texto import (
    agrupar_en_rangos,
    interpretar_posiciones,
    limpiar_nombre_de_nota,
    nombre_de_archivo_evento,
    normalizar_nombre_comic,
    titulo_con_anio,
)
from .ui import confirmar, elegir, pedir, pedir_posicion, por_numero


def archivos_de_eventos_propios():
    return [archivo for archivo in archivos_de_eventos() if es_evento_propio(archivo)]


def filas_de_evento(numeros_evento):
    """El orden de lectura agrupado por cómic: «  1–12  X-Force (2018) #1–12» (una fila por tramo seguido)."""
    filas, i = [], 0
    while i < len(numeros_evento):
        j = i
        while j + 1 < len(numeros_evento) and (numeros_evento[j + 1]["comic"], numeros_evento[j + 1]["anio_comic"]) == (
            numeros_evento[i]["comic"],
            numeros_evento[i]["anio_comic"],
        ):
            j += 1
        rango = f"{i + 1}" if i == j else f"{i + 1}–{j + 1}"
        filas.append(
            f"  {rango:>8}  {titulo_con_anio(numeros_evento[i]['comic'], numeros_evento[i]['anio_comic'])} {agrupar_en_rangos([ejemplar['numero'] for ejemplar in numeros_evento[i:j + 1]])}"
        )
        i = j + 1
    return filas


def mostrar_numeros_evento(nombre, numeros_evento, pagina=0):
    """Muestra una página del orden de lectura. Devuelve (página mostrada, total de páginas)."""
    filas = filas_de_evento(numeros_evento)
    paginas = max(1, -(-len(filas) // RESULTADOS_POR_PAGINA))
    pagina = min(max(pagina, 0), paginas - 1)
    print(
        f"\n📋 {nombre} — {len(numeros_evento)} número(s) en orden de lectura"
        + (f" · página {pagina + 1} de {paginas}" if paginas > 1 else "")
    )
    for fila in filas[pagina * RESULTADOS_POR_PAGINA : (pagina + 1) * RESULTADOS_POR_PAGINA]:
        print(fila)
    return pagina, paginas


def pedir_nombre_para_evento(texto, defecto=""):
    """Pide un nombre válido y que no exista (Enter = defecto, si hay). Para cancelar, Esc."""
    while True:
        nombre = pedir_texto(texto).strip() or defecto
        if not nombre:
            continue
        if not nombre_de_archivo_evento(nombre):
            print("❌ Ese nombre no es válido.")
        elif nombre_de_archivo_evento(nombre) in nombres_de_eventos():
            print("❌ Ya existe un evento con ese nombre.")
        else:
            return nombre


def pedir_carpeta_de_nota(defecto=""):
    """Pregunta en qué carpeta de Obsidian va la nota del evento. Devuelve "" para la de siempre («Eventos»)."""
    opciones = [CARPETA_NOTAS_EVENTOS] + sorted(
        {carpeta_de_nota(archivo) for archivo in archivos_de_eventos_propios()} - {"", CARPETA_NOTAS_EVENTOS}
    )
    print("\nCarpeta de Obsidian para la nota del evento:")
    for j, carpeta in enumerate(opciones, 1):
        print(f"  {j}. {carpeta}")
    while True:
        respuesta = pedir_texto(
            f"Elegir un número o escribir el nombre de una carpeta nueva [Enter = {defecto or CARPETA_NOTAS_EVENTOS}]: "
        ).strip()
        if not respuesta:
            return defecto
        carpeta = por_numero(respuesta, opciones) or limpiar_nombre_de_nota(respuesta)
        if not carpeta or carpeta.startswith(".") or carpeta.lower() in CARPETAS_RESERVADAS:
            print("❌ Esa carpeta no se puede usar. Escribir otro nombre.")
            continue
        return "" if carpeta == CARPETA_NOTAS_EVENTOS else carpeta


def pedir_anio(texto):
    while True:
        respuesta = pedir_texto(texto).strip()
        if not respuesta:
            return None
        if re.fullmatch(r"\d{4}", respuesta):
            return int(respuesta)
        print("❌ Escribir un año de 4 cifras, por ejemplo 2006.")


def editar_evento_propio(config, ruta):
    nombre = nombre_original_del_evento(ruta)
    numeros_evento = leer_cbl(ruta)[2]
    anios = list(anios_indicados_a_mano(ruta))
    carpeta = carpeta_de_nota(ruta)
    print(f"\n✏️  Editor del evento «{nombre}». Cada cambio se guarda al momento.")
    pagina = 0
    while True:
        pagina, paginas = mostrar_numeros_evento(nombre, numeros_evento, pagina)
        inicio, fin = anios_de_evento(ruta, numeros_evento, cargar_catalogo(descargar_si_falta=False))
        if inicio:
            print(
                f"   📅 Años: {inicio if inicio == fin else f'{inicio}–{fin}'}"
                + (" (indicados a mano)" if any(anios) else " (según las listas)")
            )
        print(
            "\n¿Qué se desea hacer?\n  1. Agregar un cómic o números\n  2. Quitar\n  3. Mover\n"
            "  4. Indicar el año de inicio y fin\n"
            f"  5. Cambiar la carpeta de la nota (ahora: {carpeta or CARPETA_NOTAS_EVENTOS})\n"
            "  0. Terminar y actualizar las notas\n"
            + ("S = página siguiente · A = página anterior · " if paginas > 1 else "")
            + "Esc = salir sin actualizar"
        )
        try:
            respuesta = pedir_texto("> ").strip()
        except Cancelado:
            print("Se sale sin actualizar las notas. Los cambios ya quedaron guardados.")
            return
        except (EOFError, KeyboardInterrupt):
            break
        if respuesta == "0":
            break
        if respuesta.lower() in ("s", "a") and paginas > 1:
            pagina += 1 if respuesta.lower() == "s" else -1
            if not 0 <= pagina < paginas:
                print("No hay más páginas." if pagina >= paginas else "Esta es la primera página.")
            continue
        try:
            if respuesta == "1":
                comic, anio_comic, numeros, extra = elegir_comic_y_numeros(
                    "\nBuscar el cómic a agregar (Esc = cancelar):\n> "
                )
                posicion_destino = pedir_posicion("¿En qué posición va?", len(numeros_evento) + 1, len(numeros_evento) + 1)
                agregados, repetidos = agregar_numeros_evento(
                    numeros_evento,
                    comic,
                    anio_comic,
                    numeros,
                    extra,
                    posicion_destino,
                )
                print(f"✅ Se agregaron {agregados} número(s)" + (f" ({repetidos} ya estaban)" if repetidos else ""))
            elif respuesta == "2":
                texto = pedir(
                    "Escribir las posiciones a quitar (ej: 3  o  5-7  o  2,9-11) o el nombre de un cómic para quitarlo completo"
                    " (Esc = cancelar):\n> "
                )
                por_posicion = bool(re.fullmatch(r"[\d,\-\s]+", texto))
                if por_posicion:
                    quitar_idx = interpretar_posiciones(texto, len(numeros_evento))
                else:
                    consulta = normalizar_nombre_comic(texto)
                    quitar_idx = [
                        posicion
                        for posicion, ejemplar in enumerate(numeros_evento, 1)
                        if consulta
                        and consulta in normalizar_nombre_comic(titulo_con_anio(ejemplar["comic"], ejemplar["anio_comic"]))
                    ]
                if not quitar_idx:
                    print("No se encontró nada que quitar.")
                    continue
                if len(quitar_idx) >= len(numeros_evento):
                    print(
                        "Un evento necesita al menos un número. Para borrarlo por completo, usar «Mi biblioteca → Quitar un evento o cómic»."
                    )
                    continue
                if (not por_posicion or len(quitar_idx) > 5) and not confirmar(
                    f"Se quitarán {len(quitar_idx)} número(s). ¿Confirmar? (s/n): "
                ):
                    continue
                numeros_evento[:] = [
                    ejemplar for posicion, ejemplar in enumerate(numeros_evento, 1) if posicion not in quitar_idx
                ]
                print(f"🗑️  Se quitaron {len(quitar_idx)} número(s).")
            elif respuesta == "3":
                texto = pedir(
                    "Indicar qué mover y adónde, por ejemplo  8 a 2  (lo que está en la posición 8 pasa a la posición 2)  o  8-10 a 2"
                    " (Esc = cancelar):\n> "
                )
                coincidencia = re.fullmatch(r"([\d,\-\s]+?)\s*(?:a|->|→|to|hasta)\s*(\d+)", texto, re.I)
                posiciones_origen = (
                    interpretar_posiciones(coincidencia.group(1), len(numeros_evento)) if coincidencia else []
                )
                if (
                    not coincidencia
                    or not posiciones_origen
                    or not (1 <= int(coincidencia.group(2)) <= len(numeros_evento))
                ):
                    print("❌ Entrada no válida. Ejemplo: 8 a 2")
                    continue
                mover = [numeros_evento[posicion - 1] for posicion in posiciones_origen]
                resto = [
                    ejemplar for posicion, ejemplar in enumerate(numeros_evento, 1) if posicion not in posiciones_origen
                ]
                destino = min(int(coincidencia.group(2)) - 1, len(resto))
                numeros_evento[:] = resto[:destino] + mover + resto[destino:]
                print(f"↕️  Se movieron {len(mover)} número(s) a la posición {destino + 1}.")
            elif respuesta == "4":
                print("Dejar vacío para calcularlo con las fechas de los números.")
                anio_inicio_nuevo, anio_fin_nuevo = pedir_anio("Año de inicio (ej: 2006): "), None
                if anio_inicio_nuevo:
                    anio_fin_nuevo = pedir_anio(f"Año de fin [Enter = {anio_inicio_nuevo}]: ") or anio_inicio_nuevo
                    if anio_fin_nuevo < anio_inicio_nuevo:
                        print("❌ El año de fin no puede ser menor que el de inicio.")
                        continue
                anios = [anio_inicio_nuevo, anio_fin_nuevo]
            elif respuesta == "5":
                carpeta = pedir_carpeta_de_nota(carpeta)
            else:
                continue
        except Cancelado:
            print("↩️  Cancelado.")
            continue
        escribir_cbl(ruta, nombre, numeros_evento, tuple(anios), carpeta)  # se guarda después de cada cambio
    generar(config)


def elegir_y_editar_evento_propio(config):
    propios = archivos_de_eventos_propios()
    if not propios:
        print("Todavía no hay eventos propios. Crear, copiar o importar uno en «Agregar…».")
        return
    archivo = elegir(propios, nombre_sin_orden, "¿Cuál se edita?")
    if archivo:
        editar_evento_propio(config, archivo)
