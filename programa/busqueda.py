"""Buscar un cómic en el catálogo y elegir qué números se agregan (lo usan «Agregar» y el editor de eventos)."""

from .catalogo import cargar_catalogo
from .teclado import pedir_texto
from .texto import buscar_por_palabras, describir_numeros, interpretar_numeros_elegidos, titulo_con_anio
from .ui import CERO, elegir, pedir


def elegir_comic(pregunta, consulta_sugerida="", con_terminar=False):
    """Pide un cómic, buscándolo en el catálogo (o escrito a mano con la opción 0).
    Devuelve (comic, anio_comic, numeros_catalogo, extra) donde extra trae los años e identificadores que conoce el
    catálogo, o "fin" si con_terminar y se escribe 0. Para cancelar, Esc.
    Con consulta_sugerida, Enter busca ese texto."""
    consulta = pedir_texto(pregunta).strip() or consulta_sugerida
    while not consulta:
        consulta = pedir(pregunta)
    if con_terminar and consulta == "0":
        return "fin"
    catalogo = cargar_catalogo()
    comic = anio_comic = None
    numeros_catalogo = []
    extra = {"anios_publicacion": {}, "id_cv": {}}
    if catalogo:
        resultados = buscar_por_palabras(
            consulta,
            [
                (f"{titulo_catalogo['comic']} {titulo_catalogo['anio_comic']}", titulo_catalogo)
                for titulo_catalogo in catalogo["titulos"].values()
            ],
        )
        resultados.sort(
            key=lambda titulo_catalogo: (
                len(titulo_catalogo["comic"]),
                titulo_catalogo["comic"],
                titulo_catalogo["anio_comic"],
            )
        )
        titulo_catalogo = elegir(
            resultados,
            lambda titulo_catalogo: f"{titulo_con_anio(titulo_catalogo['comic'], titulo_catalogo['anio_comic'])}   ({describir_numeros(titulo_catalogo['numeros'])})",
            "Elegir el número del cómic",
            opcion_cero="No está en la lista (ingresarlo a mano)",
        )
        if titulo_catalogo is not CERO:
            comic, anio_comic, numeros_catalogo = (
                titulo_catalogo["comic"],
                titulo_catalogo["anio_comic"],
                titulo_catalogo["numeros"],
            )
            extra = {
                "anios_publicacion": titulo_catalogo.get("anios_publicacion", {}),
                "id_cv": titulo_catalogo.get("id_cv", {}),
            }
    if not comic:
        comic = pedir("Nombre del cómic tal como aparece en la portada (ej: Amazing Spider-Man): ")
        anio_comic = pedir_texto("Año en que empezó ese cómic (ej: 2018): ").strip()
    return comic, anio_comic, numeros_catalogo, extra


def elegir_comic_y_numeros(
    pregunta="\nBuscar un cómic por nombre (ej: uncanny x-men, amazing spider-man):\n> ", con_terminar=False
):
    """Pide un cómic (buscándolo en el catálogo) y qué números se agregan.
    Devuelve (comic, anio_comic, numeros, extra) donde extra trae los años e identificadores que conoce el catálogo,
    o "fin" si con_terminar y se escribe 0. Para cancelar, Esc."""
    seleccion = elegir_comic(pregunta, con_terminar=con_terminar)
    if seleccion == "fin":
        return seleccion
    comic, anio_comic, numeros_catalogo, extra = seleccion

    while True:
        if numeros_catalogo:
            print(f"\nSe conocen {describir_numeros(numeros_catalogo, max_partes=8)}")
            respuesta = pedir_texto(
                "Presionar Enter para agregarlos todos, o escribir cuáles (ej: 1-20  o  1-20,300-317):\n> "
            ).strip()
            if not respuesta:
                return comic, anio_comic, list(numeros_catalogo), extra
        else:
            respuesta = pedir("¿Qué números se agregan? (ej: 1-50):\n> ")
        numeros = interpretar_numeros_elegidos(respuesta, numeros_catalogo)
        if numeros:
            return comic, anio_comic, numeros, extra
        print("❌ Entrada no válida. Escribir un número o un rango, por ejemplo 1-20.")
