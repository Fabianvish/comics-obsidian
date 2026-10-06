"""Menú «Personajes»: sugerir y rellenar personajes con la API de Comic Vine."""

from .catalogo import cargar_catalogo
from .comicvine import cache_personajes, contar_personajes
from .configurar import pedir_clave_api
from .constantes import PAUSA_ENTRE_PETICIONES, PETICIONES_POR_HORA
from .errores import ErrorAPI, LimiteAPI
from .generador import generar
from .md import leer_propiedad_lista
from .personajes import (
    agregar_personajes_a_nota,
    destinos_para_personajes,
    nombre_de_personaje,
    nombre_para_nota,
    nombres_de_notas_de_personajes,
)
from .teclado import pedir_texto
from .texto import interpretar_posiciones, normalizar_nombre_comic
from .ui import confirmar, elegir, pedir


def explicar_consultas_a_la_api(ids_cv, cache):
    numeros_sin_consultar = len([i for i in ids_cv if i not in cache["numeros"]])
    if numeros_sin_consultar == 0:
        print(f"Los {len(ids_cv)} números ya estaban consultados: no hace falta usar la API.")
        return True
    minutos = max(1, round(numeros_sin_consultar * PAUSA_ENTRE_PETICIONES / 60))
    print(
        f"Se consultarán {numeros_sin_consultar} número(s) en Comic Vine ({len(ids_cv) - numeros_sin_consultar} ya están guardados): unos {minutos} minuto(s)."
    )
    if numeros_sin_consultar > PETICIONES_POR_HORA:
        print(
            f"Atención: el límite es de 200 por hora, así que se detendrá a las {PETICIONES_POR_HORA} y se podrá retomar más tarde; lo consultado queda guardado."
        )
    return confirmar("¿Continuar? (s/n): ")


def sugerir_personajes(config):
    if not pedir_clave_api(config):
        return
    catalogo = cargar_catalogo(descargar_si_falta=False)
    objetivos = destinos_para_personajes(config, catalogo)
    if not objetivos:
        print("Primero hay que agregar un evento o seguir un cómic.")
        return
    elegido = elegir(objetivos, lambda objetivo: objetivo[0], "¿Para cuál?")
    if not elegido:
        return
    _, nombre, nota, ids_cv = elegido
    if not ids_cv:
        print("Ese evento o cómic no tiene identificadores de Comic Vine (¿se descargó el catálogo en «Configuración → Actualizar el catálogo»?).")
        return
    cache = cache_personajes()
    if not explicar_consultas_a_la_api(ids_cv, cache):
        return
    try:
        cuenta, nombres = contar_personajes(config, ids_cv, cache)
    except LimiteAPI as error:
        print(f"⏳ {error}")
        return
    if not cuenta:
        print("Comic Vine no tiene personajes registrados para estos números.")
        return
    existentes = nombres_de_notas_de_personajes(config)
    actuales = (
        {nombre_de_personaje(actual) for actual in leer_propiedad_lista(nota.read_text(encoding="utf-8"), "personajes")}
        if nota.exists()
        else set()
    )
    mas_frecuentes = sorted(cuenta.items(), key=lambda par_id_cuenta: (-par_id_cuenta[1], nombres[par_id_cuenta[0]]))[
        :15
    ]
    print(f"\nPersonajes que más aparecen en {nombre} ({len(ids_cv)} números):")
    for j, (id_personaje, cantidad_de_numeros) in enumerate(mas_frecuentes, 1):
        nombre = nombre_para_nota(nombres[id_personaje], existentes)
        print(
            f"  {j:2d}. {nombre}   ({cantidad_de_numeros} de {len(ids_cv)} números)"
            + ("   ✓ ya está" if normalizar_nombre_comic(nombre) in actuales else "")
        )
    while True:
        seleccion = pedir("¿Cuáles se agregan? (ej: 1,3,5-8  o  todos; Esc = ninguno): ").lower()
        elegidos = (
            list(range(1, len(mas_frecuentes) + 1))
            if seleccion == "todos"
            else interpretar_posiciones(seleccion, len(mas_frecuentes))
        )
        if elegidos:
            break
        print(f"❌ Escribir números de la lista (1 a {len(mas_frecuentes)}) o «todos».")
    cantidad_agregados = agregar_personajes_a_nota(
        nota, [nombre_para_nota(nombres[mas_frecuentes[j - 1][0]], existentes) for j in elegidos]
    )
    print(f"👤 Se agregaron {cantidad_agregados} personaje(s) a «{nombre}».")
    generar(config)


def rellenar_todos_los_personajes(config):
    if not pedir_clave_api(config):
        return
    catalogo = cargar_catalogo(descargar_si_falta=False)
    objetivos = destinos_para_personajes(config, catalogo)
    if not objetivos:
        print("Primero hay que agregar un evento o seguir un cómic.")
        return
    respuesta = pedir_texto("¿Cuántos personajes por evento o cómic? [Enter = 10]: ").strip()
    cantidad_maxima = int(respuesta) if respuesta.isdigit() and int(respuesta) > 0 else 10
    incluir_con_personajes = confirmar(
        "¿Incluir también los que ya tienen personajes escritos? (s/n) [Enter = no, no se modifican]: "
    )
    elegibles = []
    for _, nombre, nota, ids_cv in objetivos:
        if not ids_cv or not nota.exists():
            continue
        if not incluir_con_personajes and leer_propiedad_lista(nota.read_text(encoding="utf-8"), "personajes"):
            continue
        elegibles.append((nombre, nota, ids_cv))
    if not elegibles:
        print("No hay nada que rellenar: todos ya tienen personajes (o no tienen identificadores de Comic Vine).")
        return
    cache = cache_personajes()
    todos = list(dict.fromkeys(i for _, _, ids_cv in elegibles for i in ids_cv))
    print(f"Se rellenarán {len(elegibles)} evento(s)/cómic(s).")
    if not explicar_consultas_a_la_api(todos, cache):
        return
    existentes = nombres_de_notas_de_personajes(config)
    hechos = 0
    try:
        for nombre, nota, ids_cv in elegibles:
            cuenta, nombres = contar_personajes(config, ids_cv, cache, mostrar=False)
            mas_frecuentes = sorted(
                cuenta.items(), key=lambda par_id_cuenta: (-par_id_cuenta[1], nombres[par_id_cuenta[0]])
            )[:cantidad_maxima]
            agregados = agregar_personajes_a_nota(
                nota, [nombre_para_nota(nombres[id_personaje], existentes) for id_personaje, _ in mas_frecuentes]
            )
            hechos += 1
            print(f"  ✓ {nombre}: {agregados} personaje(s)")
    except LimiteAPI as error:
        print(f"⏳ {error}\n   Lo consultado quedó guardado: al volver a elegir esta opción se continúa donde quedó.")
    except ErrorAPI as error:
        print(f"❌ {error}")
    if hechos:
        generar(config)
