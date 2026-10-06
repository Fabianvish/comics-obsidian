"""Menú «Agregar…»: eventos del catálogo, seguir un cómic y eventos propios (crear, copiar, importar)."""

import xml.etree.ElementTree as ET

from .busqueda import elegir_comic, elegir_comic_y_numeros
from .catalogo import cargar_catalogo, descargar_listas_de_github, leer_lista_del_catalogo
from .config import guardar_config
from .editor_evento import editar_evento_propio, pedir_carpeta_de_nota, pedir_nombre_para_evento
from .generador import generar
from .importacion import aplicar_reconocimiento, leer_origen, reconocer_comics
from .listados import pedir_posicion_de_evento
from .listas import (
    agregar_numeros_evento,
    archivos_de_eventos,
    carpeta_de_nota,
    escribir_cbl,
    insertar_eventos,
    leer_ejemplares_de_cbl,
    nombre_original_del_evento,
    nombre_sin_orden,
)
from .teclado import Cancelado, pedir_texto
from .texto import (
    buscar_por_palabras,
    clave_orden_natural,
    interpretar_posiciones,
    nombre_de_archivo_evento,
    nombre_visible_evento,
    normalizar_nombre_comic,
    normalizar_numero,
    titulo_con_anio,
)
from .ui import elegir, paginar, pedir, ver_paginado


def agregar_evento(config):
    consulta = pedir("\nBuscar un evento por nombre (ej: second coming), o pegar un enlace de GitHub:\n> ").strip('"')
    if consulta.startswith("http"):
        try:
            listas_nuevas = descargar_listas_de_github(consulta)
        except Exception as error:
            print(f"❌ No se pudo descargar: {error}")
            return
    else:
        catalogo = cargar_catalogo()
        if not catalogo:
            return
        resultados = buscar_por_palabras(
            consulta,
            [
                (f"{lista_catalogo['nombre_visible']} {lista_catalogo['categoria']}", (i, lista_catalogo))
                for i, lista_catalogo in enumerate(catalogo["listas"])
            ],
        )
        resultados.sort(
            key=lambda resultado: (
                not resultado[1]["categoria"].startswith("Events"),
                clave_orden_natural(resultado[1]["ruta"]),
            )
        )
        if not resultados:
            print("No se encontró nada con ese nombre. Probar con menos palabras o en inglés.")
            return
        while True:
            seleccion = interpretar_posiciones(
                paginar(
                    resultados,
                    lambda resultado: f"{resultado[1]['nombre_visible']}  ({resultado[1]['cantidad']} números)  [{resultado[1]['categoria']}]",
                    "Elegir uno o varios (ej: 3  o  1,4  o  2-6)",
                ),
                len(resultados),
            )
            if seleccion:
                break
            print(f"❌ Escribir números de la lista (1 a {len(resultados)}).")
        listas_nuevas = [
            (resultados[j - 1][1]["nombre"], leer_lista_del_catalogo(resultados[j - 1][1]["ruta"])) for j in seleccion
        ]

    actuales = archivos_de_eventos()
    ya_agregados = {nombre_sin_orden(archivo) for archivo in actuales}
    listas_nuevas = [
        (nombre_evento, contenido) for nombre_evento, contenido in listas_nuevas if nombre_evento not in ya_agregados
    ]
    if not listas_nuevas:
        print("Ya estaba agregado.")
        return
    insertar_eventos(
        [(nombre, lambda ruta, datos=datos: ruta.write_bytes(datos)) for nombre, datos in listas_nuevas],
        pedir_posicion_de_evento(config),
    )
    print(f"📥 {len(listas_nuevas)} evento(s) agregado(s)")
    generar(config)


def seguir_comic(config):
    comic, anio_comic, numeros, _ = elegir_comic_y_numeros()

    # Si ya seguías este cómic, los números nuevos se SUMAN a los que ya tenías
    seguidos = config.get("seguidos", [])
    previo = next(
        (
            seguido
            for seguido in seguidos
            if normalizar_nombre_comic(seguido["comic"]) == normalizar_nombre_comic(comic)
            and seguido["anio_comic"] == anio_comic
        ),
        None,
    )
    if previo:
        conocidos = {normalizar_numero(numero) for numero in previo["numeros"]}
        numeros_nuevos = [numero for numero in numeros if normalizar_numero(numero) not in conocidos]
        previo["numeros"] = sorted(previo["numeros"] + numeros_nuevos, key=clave_orden_natural)
        total = len(previo["numeros"])
        if numeros_nuevos:
            print(
                f"📥 {titulo_con_anio(comic, anio_comic)}: se agregaron {len(numeros_nuevos)} número(s) nuevo(s); ahora son {total} en seguimiento"
            )
        else:
            print(
                f"ℹ️  Esos números de {titulo_con_anio(comic, anio_comic)} ya estaban en seguimiento ({total} en total)"
            )
    else:
        seguidos.append({"comic": comic, "anio_comic": anio_comic, "numeros": numeros})
        print(f"📥 En seguimiento: {titulo_con_anio(comic, anio_comic)}, {len(numeros)} números")
    config["seguidos"] = seguidos
    guardar_config(config)
    generar(config)


def guardar_eventos_propios(config, eventos):
    """Guarda eventos nuevos [(nombre, numeros_evento, carpeta)] juntos, en la posición que se elija, y devuelve sus rutas."""
    posicion = pedir_posicion_de_evento(config)
    return insertar_eventos(
        [
            (
                nombre_de_archivo_evento(nombre),
                lambda ruta, nombre=nombre, numeros_evento=numeros_evento, carpeta=carpeta: escribir_cbl(
                    ruta, nombre, numeros_evento, carpeta=carpeta
                ),
            )
            for nombre, numeros_evento, carpeta in eventos
        ],
        posicion,
    )


def guardar_evento_propio(config, nombre, numeros_evento, carpeta=""):
    """Guarda el evento nuevo en la posición que se elija y devuelve la ruta de su archivo."""
    return guardar_eventos_propios(config, [(nombre, numeros_evento, carpeta)])[0]


def crear_evento_propio(config):
    nombre = pedir_nombre_para_evento("\nNombre del evento (Esc = cancelar): ")
    carpeta = pedir_carpeta_de_nota()
    numeros_evento = []
    print("Agregar los cómics en el orden de lectura deseado. Cada uno se suma al final.")
    while True:
        print(f"\nEl evento tiene {len(numeros_evento)} número(s).")
        seleccion = elegir_comic_y_numeros(
            "Buscar un cómic para agregar (0 = terminar, Esc = cancelar el evento):\n> ", con_terminar=True
        )
        if seleccion == "fin":
            break
        agregados, repetidos = agregar_numeros_evento(numeros_evento, *seleccion)
        print(f"✅ Se agregaron {agregados} número(s)" + (f" ({repetidos} ya estaban)" if repetidos else ""))
    if not numeros_evento:
        print("No se creó el evento porque no tiene ningún número.")
        return
    guardar_evento_propio(config, nombre, numeros_evento, carpeta)
    print(
        f"📥 Evento «{nombre}» creado con {len(numeros_evento)} número(s). Para modificarlo, usar «Editar un evento propio»."
    )
    generar(config)


def copiar_evento(config):
    consulta = pedir("\nBuscar el evento a copiar (ej: civil war):\n> ")
    catalogo = cargar_catalogo()
    if not catalogo:
        return
    resultados = buscar_por_palabras(
        consulta,
        [
            (f"{lista_catalogo['nombre_visible']} {lista_catalogo['categoria']}", (i, lista_catalogo))
            for i, lista_catalogo in enumerate(catalogo["listas"])
        ],
    )
    resultados.sort(
        key=lambda resultado: (
            not resultado[1]["categoria"].startswith("Events"),
            clave_orden_natural(resultado[1]["ruta"]),
        )
    )
    elegido = elegir(
        resultados,
        lambda resultado: f"{resultado[1]['nombre_visible']}  ({resultado[1]['cantidad']} números)  [{resultado[1]['categoria']}]",
        "Elegir el evento a copiar",
        paginado=True,
    )
    if not elegido:
        return
    lista_catalogo = elegido[1]
    raiz = ET.fromstring(leer_lista_del_catalogo(lista_catalogo["ruta"]))
    numeros_evento = leer_ejemplares_de_cbl(raiz)[0]
    defecto = f"{lista_catalogo['nombre_visible']} (mi versión)"
    nombre = pedir_nombre_para_evento(f"Nombre de la copia [Enter = {defecto}]: ", defecto)
    ruta = guardar_evento_propio(config, nombre, numeros_evento, pedir_carpeta_de_nota())
    print(f"📥 «{lista_catalogo['nombre_visible']}» copiado como «{nombre}». Ahora se puede editar.")
    editar_evento_propio(config, ruta)


def archivo_de_evento_con_nombre(nombres_archivo):
    """Archivo del evento ya agregado que se llama como alguno de esos nombres (None si no hay)."""
    return next(
        (
            archivo
            for archivo in archivos_de_eventos()
            if nombre_sin_orden(archivo) in nombres_archivo
        ),
        None,
    )


def elegir_nombre_de_importacion(nombre_original, nombres_reservados):
    """Pregunta el nombre del evento importado. Devuelve (nombre, archivo_a_reemplazar); (None, None) si se omite."""
    defecto = nombre_visible_evento(nombre_original)
    nombre = pedir_texto(f"Nombre del evento [Enter = {defecto}]: ").strip() or defecto
    while True:
        nombre_archivo = nombre_de_archivo_evento(nombre)
        if not nombre_archivo or nombre_archivo in nombres_reservados:
            print(
                "❌ Ese nombre no es válido."
                if not nombre_archivo
                else f"Otra lista de esta importación ya se llama «{nombre}»."
            )
            nombre = pedir("Nombre del evento (0 = no importarlo): ")
            if nombre == "0":
                return None, None
            continue
        existente = archivo_de_evento_con_nombre(
            {nombre_archivo} | ({nombre_de_archivo_evento(nombre_original)} if nombre == defecto else set())
        )
        if not existente:
            return nombre, None
        print(
            f"Ya existe el evento «{nombre_original_del_evento(existente)}».\n"
            "  1. Reemplazarlo por la versión nueva (lo leído y la nota se conservan)\n"
            "  2. Importarlo con otro nombre\n"
            "  0. No importarlo"
        )
        respuesta = pedir("> ")
        while respuesta not in ("0", "1", "2"):
            respuesta = pedir("Elegir 1, 2 o 0: ")
        if respuesta == "1":
            return nombre_original_del_evento(existente), existente
        if respuesta == "0":
            return None, None
        nombre = pedir("Nombre del evento (0 = no importarlo): ")
        if nombre == "0":
            return None, None


def resolver_no_reconocidos(no_reconocidos, reconocidos):
    """Pregunta qué hacer con cada cómic no reconocido. Completa reconocidos y devuelve los cómics que se quitan."""
    quitados = set()
    for i, ((comic, anio_comic), cantidad) in enumerate(no_reconocidos, 1):
        print(f"\n{i}/{len(no_reconocidos)}. {titulo_con_anio(comic, anio_comic)}: {cantidad} número(s)")
        respuesta = (
            pedir_texto(
                "  1. Buscarlo a mano\n  2. Dejarlo como viene\n  3. Quitarlo\n"
                "  T. Dejar como vienen todos los que faltan\nEnter = dejarlo como viene\n> "
            )
            .strip()
            .lower()
        )
        if respuesta == "t":
            break
        if respuesta == "3":
            quitados.add((comic, anio_comic))
            print(f"🗑️  Se quitará {titulo_con_anio(comic, anio_comic)}.")
        elif respuesta == "1":
            try:
                seleccion = elegir_comic(
                    f"Buscar el cómic [Enter = {comic}, Esc = dejarlo como viene]:\n> ", consulta_sugerida=comic
                )
            except Cancelado:
                print("Se deja como viene.")
                continue
            comic_elegido, anio_elegido, _, extra = seleccion
            reconocidos[(comic, anio_comic)] = {"comic": comic_elegido, "anio_comic": anio_elegido, **extra}
            print(f"✅ Se usará {titulo_con_anio(comic_elegido, anio_elegido)}.")
    return quitados


def importar_evento(config):
    origen = (
        pedir("\nRuta de un archivo .cbl o de una carpeta con varios, o un enlace (Esc = cancelar):\n> ")
        .strip('"')
        .strip("'")
    )
    listas_leidas = leer_origen(origen)
    catalogo = cargar_catalogo()
    if not catalogo:
        print("⚠️  Sin catálogo no se pueden reconocer los cómics: se importan como vienen.")
    nuevos, reemplazados, nombres_reservados, carpeta = [], [], set(), ""
    for nombre_original, raiz in listas_leidas:
        ejemplares, ids_comic = leer_ejemplares_de_cbl(raiz)
        if not ejemplares:
            print(f"\n⚠️  «{nombre_original}» no tiene números; se omite.")
            continue
        reconocidos, no_reconocidos = reconocer_comics(ejemplares, ids_comic, catalogo)
        cantidad_no_reconocida = sum(cantidad for _, cantidad in no_reconocidos)
        print(
            f"\n📄 «{nombre_visible_evento(nombre_original)}»: "
            f"{len(ejemplares) - cantidad_no_reconocida} de {len(ejemplares)} números reconocidos."
        )
        quitados = set()
        if no_reconocidos and catalogo:
            print("No reconocidos:")
            ver_paginado(
                list(enumerate(no_reconocidos, 1)),
                lambda fila: f"{fila[0]}. {titulo_con_anio(*fila[1][0])}: {fila[1][1]} número(s)",
            )
            print("Sin reconocer, el evento funciona igual, pero esos números pueden quedar sin años ni personajes.")
            quitados = resolver_no_reconocidos(no_reconocidos, reconocidos)
        numeros_evento = aplicar_reconocimiento(ejemplares, reconocidos, quitados)
        if not numeros_evento:
            print("No se importa porque no quedó ningún número.")
            continue
        nombre, existente = elegir_nombre_de_importacion(nombre_original, nombres_reservados)
        if not nombre:
            continue
        nombres_reservados.add(nombre_de_archivo_evento(nombre))
        carpeta = pedir_carpeta_de_nota(carpeta_de_nota(existente) if existente else carpeta)
        if existente:
            escribir_cbl(existente, nombre, numeros_evento, carpeta=carpeta)
            reemplazados.append(existente)
            print(f"🔁 «{nombre}» reemplazado ({len(numeros_evento)} números).")
        else:
            nuevos.append((nombre, numeros_evento, carpeta))
    rutas = guardar_eventos_propios(config, nuevos) if nuevos else []
    rutas += reemplazados
    if not rutas:
        print("No se importó ningún evento.")
        return
    if len(rutas) == 1:
        print("📥 Evento importado. Ahora se puede editar.")
        editar_evento_propio(config, rutas[0])
        return
    print(f"📥 Se importaron {len(rutas)} eventos. Para modificarlos, usar «Editar un evento propio».")
    generar(config)
