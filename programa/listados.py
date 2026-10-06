"""Lo que se muestra de la biblioteca en la consola y se usa desde varios menús."""

from .listas import archivos_de_eventos, es_evento_propio
from .texto import titulo_con_anio
from .ui import pedir_posicion, ver_paginado


def ver_eventos_y_comics(config, solo_eventos=False):
    actuales = archivos_de_eventos()
    print("\nEventos (en orden de lectura):" if actuales else "\nAún no hay eventos.")
    ver_paginado(actuales, lambda archivo: archivo.stem + ("   ✏️ propio" if es_evento_propio(archivo) else ""))
    if not solo_eventos:
        seguidos = config.get("seguidos", [])
        print("\nCómics en seguimiento:" if seguidos else "\nAún no hay cómics en seguimiento.")
        ver_paginado(
            seguidos,
            lambda seguido: f"{titulo_con_anio(seguido['comic'], seguido['anio_comic'])}"
            f"  (#{seguido['numeros'][0]} al #{seguido['numeros'][-1]})",
        )


def pedir_posicion_de_evento(config):
    """Muestra los eventos y pregunta en qué posición va uno nuevo (Enter = al final)."""
    actuales = archivos_de_eventos()
    if not actuales:
        return 1
    ver_eventos_y_comics(config, solo_eventos=True)
    return pedir_posicion("¿En qué posición va entre los eventos?", len(actuales) + 1, len(actuales) + 1)
