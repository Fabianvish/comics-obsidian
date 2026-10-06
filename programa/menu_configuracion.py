"""Menú «Configuración»: carpetas, equipos, catálogo, respaldos y emparejar archivos a mano."""

import io
import re
import shutil
import zipfile
from pathlib import Path

from .archivos import emparejar_archivos
from .catalogo import actualizar_catalogo
from .config import activar_estado, guardar_config
from .configurar import carpeta_notas, carpetas_archivos_comics, pedir_carpeta_de_comics
from .constantes import CARPETA_ESTADO, CARPETA_RESPALDOS
from .equipos import equipo_actual, leer_equipos, olvidar_equipo, ruta_para_este_sistema
from .generador import generar
from .listas import reunir_ejemplares
from .respaldo import destino_de_archivo_del_respaldo, respaldar
from .rutas import RUTAS
from .texto import buscar_por_palabras, clave_de_numero, clave_orden_natural, describir_numeros, titulo_con_anio
from .ui import confirmar, elegir, pedir, por_numero


def cambiar_carpeta_notas(config):
    print(f"Carpeta de notas actual: {config.get('notas') or '(sin configurar)'}")
    carpeta_estado_anterior, notas_anterior = RUTAS.estado_dir, config.pop("notas", None)
    try:
        base = carpeta_notas(config)
    except KeyboardInterrupt:  # si se cancela, queda la carpeta que estaba
        if notas_anterior:
            config["notas"] = notas_anterior
        raise
    base.mkdir(parents=True, exist_ok=True)
    carpeta_estado_nueva = base / CARPETA_ESTADO
    if (
        carpeta_estado_anterior
        and carpeta_estado_nueva != carpeta_estado_anterior
        and not (carpeta_estado_nueva / "estado.json").exists()
        and carpeta_estado_anterior.exists()
    ):
        if confirmar("¿Copiar los eventos, cómics en seguimiento e historial al nuevo lugar? (s/n): "):
            shutil.copytree(carpeta_estado_anterior, carpeta_estado_nueva, dirs_exist_ok=True)
    activar_estado(config)
    generar(config)


def cambiar_carpetas_comics(config):
    """Lista las carpetas donde se buscan cómics y permite agregar o quitar sin perder las demás."""
    carpetas = [str(carpeta) for carpeta in carpetas_archivos_comics(config)]
    cambios = False
    try:
        while True:
            print("\nCarpetas de cómics:" if carpetas else "\nAún no hay carpetas de cómics.")
            for posicion, carpeta in enumerate(carpetas, 1):
                print(f"  {posicion}. {carpeta}" + ("" if Path(carpeta).is_dir() else "   ⚠️ no se encuentra"))
            opciones = "A = agregar carpeta" + (", Q = quitar una" if carpetas else "")
            respuesta = pedir(f"{opciones}, 0 = volver\n> ").lower()
            if respuesta == "0":
                break
            if respuesta == "a":
                ruta = pedir_carpeta_de_comics("¿Qué carpeta agregar?")
                if str(ruta) in carpetas:
                    print("Esa carpeta ya está en la lista.")
                    continue
                carpetas.append(str(ruta))
            elif respuesta == "q" and carpetas:
                carpeta = por_numero(pedir("¿Número de la carpeta a quitar? (Esc = cancelar)\n> "), carpetas)
                if not carpeta:
                    print(f"❌ Escribir un número de la lista (1 a {len(carpetas)}).")
                    continue
                if not confirmar(f"¿Dejar de buscar cómics en «{carpeta}»? (s/n): "):
                    continue
                carpetas.remove(carpeta)
            else:
                continue
            config["comics"] = list(carpetas)
            guardar_config(config)
            cambios = True
    finally:
        if cambios:  # también al cancelar con Esc: lo ya agregado o quitado queda guardado
            generar(config)


def elegir_otro_equipo(nombres, pregunta):
    """Pide el número de un equipo que no sea este PC. Devuelve su nombre o None."""
    nombre = por_numero(pedir(pregunta), nombres)
    if not nombre:
        print(f"❌ Escribir un número de la lista (1 a {len(nombres)}).")
    elif nombre == equipo_actual():
        print("Ese es este PC.")
        return None
    return nombre


def ver_equipos(config):
    """Los PC donde se lee, con sus carpetas de cómics. Permite usar en este PC las rutas de otro."""
    actual = equipo_actual()
    while True:
        equipos = leer_equipos()
        nombres = sorted(equipos, key=lambda nombre: (nombre != actual, nombre.lower()))
        print("\nEquipos donde lees:")
        for posicion, nombre in enumerate(nombres, 1):
            datos = equipos[nombre]
            print(
                f"  {posicion}. {nombre}  ({datos.get('sistema', '?')}, último uso: {datos.get('ultimo_uso', '?')})"
                + ("   ← este PC" if nombre == actual else "")
            )
            for carpeta in datos.get("comics", []):
                existe = ruta_para_este_sistema(carpeta).is_dir()
                print(f"       📁 {carpeta}" + ("" if existe else "   ⚠️ no se encuentra en este PC"))
            if not datos.get("comics"):
                print("       (sin carpetas de cómics)")
        if len(nombres) < 2:
            print("Cuando uses el programa en otro PC con este mismo vault, aparecerá aquí.")
            return
        respuesta = pedir("U = usar en este PC las carpetas de otro equipo, Q = olvidar un equipo, 0 = volver\n> ").lower()
        if respuesta == "0":
            return
        if respuesta == "u":
            nombre = elegir_otro_equipo(nombres, "¿Las carpetas de qué equipo? (número)\n> ")
            if not nombre or not equipos[nombre].get("comics"):
                continue
            print(
                f"Las carpetas de cómics de {actual} se reemplazan por las de {nombre} "
                "(solo las rutas; no se copian archivos)."
            )
            if not confirmar("¿Confirmar? (s/n): "):
                continue
            config["comics"] = [str(ruta_para_este_sistema(carpeta)) for carpeta in equipos[nombre]["comics"]]
            guardar_config(config)
            generar(config)
            return
        if respuesta == "q":
            nombre = elegir_otro_equipo(nombres, "¿Qué equipo se olvida? (número)\n> ")
            if nombre and confirmar(f"¿Olvidar {nombre} y sus carpetas de cómics? (s/n): "):
                olvidar_equipo(nombre)


def actualizar_catalogo_desde_menu(config):
    if actualizar_catalogo():
        generar(config)


def describir_respaldo(archivo_respaldo):
    """«2026-10-03 17:47   (120 notas, 8 eventos)»."""
    with zipfile.ZipFile(archivo_respaldo) as archivo_zip:
        nombres = archivo_zip.namelist()
    coincidencia = re.match(r"(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})", archivo_respaldo.stem)
    fecha = (
        f"{coincidencia.group(1)} {coincidencia.group(2)}:{coincidencia.group(3)}" if coincidencia else archivo_respaldo.stem
    )
    notas = sum(1 for nombre in nombres if nombre.startswith("notas/"))
    eventos = sum(1 for nombre in nombres if nombre.endswith(".cbl"))
    return f"{fecha}   ({notas} notas, {eventos} eventos)"


def restaurar_respaldo(config):
    respaldos = sorted(CARPETA_RESPALDOS.glob("*.zip"), reverse=True) if CARPETA_RESPALDOS.is_dir() else []
    if not respaldos:
        print("Aún no hay respaldos. Se crean automáticamente cada vez que se actualizan las notas.")
        return
    print("\nRespaldos disponibles (el más nuevo primero):")
    elegido = elegir(respaldos, describir_respaldo, "¿Cuál se restaura?")
    if not elegido:
        return
    contenido = elegido.read_bytes()  # se lee ahora: la copia de seguridad previa podría borrar el respaldo más antiguo
    print("Esto reemplaza las notas, eventos, cómics en seguimiento e historial de leídos por los del respaldo.")
    print("Antes se guarda una copia del estado actual, por si es necesario volver atrás.")
    if not confirmar("¿Confirmar? (s/n): "):
        return
    base = carpeta_notas(config)
    respaldar(base)
    with zipfile.ZipFile(io.BytesIO(contenido)) as archivo_respaldo:
        miembros = [coincidencia for coincidencia in archivo_respaldo.namelist() if not coincidencia.endswith("/")]
        if any(coincidencia.endswith(".cbl") for coincidencia in miembros):
            for archivo in RUTAS.carpeta_eventos.glob("*.cbl"):
                archivo.unlink()
        cantidad = 0
        for coincidencia in miembros:
            destino = destino_de_archivo_del_respaldo(coincidencia, base)
            if destino is None:
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(archivo_respaldo.read(coincidencia))
            cantidad += 1
    activar_estado(config)
    print(f"♻️  Se restauraron {cantidad} archivos del respaldo.")
    generar(config)


def emparejar_a_mano(config):
    carpetas_de_archivos = [carpeta for carpeta in carpetas_archivos_comics(config) if carpeta.is_dir()]
    if not carpetas_de_archivos:
        print("Primero hay que indicar la carpeta de cómics en «Configuración → Carpetas de cómics de este PC».")
        return
    ejemplares = reunir_ejemplares(config)
    _, sin_emparejar, _ = emparejar_archivos(carpetas_de_archivos, ejemplares, config.get("emparejados"))
    if not sin_emparejar:
        print("🎉 No hay archivos sin emparejar.")
        return
    archivo = elegir(sin_emparejar, lambda archivo: archivo.name, "¿Qué archivo se empareja?", paginado=True)
    if not archivo:
        return
    consulta = pedir(f"\n«{archivo.name}»\n¿De qué cómic es? Escribir parte del nombre (ej: x-force):\n> ")
    titulos = sorted({(ejemplar["comic"], ejemplar["anio_comic"]) for ejemplar in ejemplares.values()})
    resultados = buscar_por_palabras(
        consulta,
        [
            (f"{comic_candidato} {anio_candidato}", (comic_candidato, anio_candidato))
            for comic_candidato, anio_candidato in titulos
        ],
    )
    if not resultados:
        print(
            "Ese cómic no está en los eventos ni en los cómics en seguimiento. Agregarlo primero con «Agregar…»."
        )
        return
    elegido = elegir(resultados, lambda titulo: titulo_con_anio(*titulo), "Elegir el cómic", paginado=True)
    if not elegido:
        return
    comic, anio_comic = elegido
    disponibles = sorted(
        {
            ejemplar["numero"]
            for ejemplar in ejemplares.values()
            if (ejemplar["comic"], ejemplar["anio_comic"]) == (comic, anio_comic)
        },
        key=clave_orden_natural,
    )
    print(
        f"En la biblioteca hay de {titulo_con_anio(comic, anio_comic)}: {describir_numeros(disponibles, max_partes=8)}"
    )
    numero = pedir("¿Qué número es este archivo?\n> ").lstrip("#")
    clave_ejemplar = clave_de_numero(comic, anio_comic, numero) if numero else ""
    if clave_ejemplar not in ejemplares:
        print("❌ Ese número no está en la biblioteca.")
        return
    config.setdefault("emparejados", {})[archivo.name] = clave_ejemplar
    guardar_config(config)
    print(f"🔗 «{archivo.name}» quedó emparejado como {titulo_con_anio(comic, anio_comic)} #{numero}.")
    generar(config)


def ver_emparejados(config):
    emparejados = config.get("emparejados", {})
    if not emparejados:
        print("No hay archivos emparejados a mano.")
        return
    ejemplares = reunir_ejemplares(config)

    def describir(item):
        nombre, clave_ejemplar = item
        ejemplar = ejemplares.get(clave_ejemplar)
        if not ejemplar:
            return f"{nombre}  →  (ya no está en la biblioteca)"
        return f"{nombre}  →  {titulo_con_anio(ejemplar['comic'], ejemplar['anio_comic'])} #{ejemplar['numero']}"

    elegido = elegir(sorted(emparejados.items()), describir, "¿Cuál se quita?")
    if elegido:
        del config["emparejados"][elegido[0]]
        guardar_config(config)
        print("🗑️  Emparejamiento quitado.")
        generar(config)
