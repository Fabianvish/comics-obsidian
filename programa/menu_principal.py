"""Menú principal y arranque del programa."""

from .config import activar_estado, guardar_config, leer_config_local
from .configurar import carpeta_notas, pedir_clave_api
from .editor_evento import archivos_de_eventos_propios, elegir_y_editar_evento_propio
from .equipos import equipo_actual
from .errores import reportar_error
from .generador import generar
from .listados import ver_eventos_y_comics
from .menu_agregar import agregar_evento, copiar_evento, crear_evento_propio, importar_evento, seguir_comic
from .menu_biblioteca import quitar_evento_o_comic, revisar_cambios_eventos
from .menu_configuracion import (
    actualizar_catalogo_desde_menu,
    cambiar_carpeta_notas,
    cambiar_carpetas_comics,
    emparejar_a_mano,
    restaurar_respaldo,
    ver_emparejados,
    ver_equipos,
)
from .menu_personajes import rellenar_todos_los_personajes, sugerir_personajes
from .ui import Menu, Opcion, pedir


def preparar(config):
    """Pregunta (la primera vez) dónde van las notas y activa el estado que vive en el vault."""
    primera_vez = "notas" not in config
    base = carpeta_notas(config)
    if primera_vez:
        base.mkdir(parents=True, exist_ok=True)
    while not base.is_dir():
        print(
            f"\n❌ No se encuentra la carpeta de notas:\n   {base}\n   ¿Está conectado el disco o disponible OneDrive?"
        )
        respuesta = pedir("0 = salir, 6 = elegir otra carpeta: ")
        while respuesta not in ("0", "6"):
            respuesta = pedir("Escribir 0 o 6: ")
        if respuesta == "0":
            return False
        config.pop("notas", None)
        guardar_config(config)
        base = carpeta_notas(config)
        base.mkdir(parents=True, exist_ok=True)
    activar_estado(config)
    return True


# Todo el árbol de menús está aquí; cada módulo menu_* solo define las acciones.
menu_agregar = Menu(
    "➕ Agregar",
    [
        Opcion("1", "Evento del catálogo", agregar_evento),
        Opcion("2", "Seguir un cómic", seguir_comic),
        Opcion("3", "Crear un evento propio desde cero", crear_evento_propio),
        Opcion("4", "Copiar un evento para editarlo", copiar_evento),
        Opcion("5", "Importar un orden de lectura (archivo .cbl, carpeta o enlace)", importar_evento),
    ],
)

menu_biblioteca = Menu(
    "📖 Mi biblioteca",
    [
        Opcion("1", "Ver eventos y cómics", ver_eventos_y_comics),
        Opcion(
            "2",
            lambda: f"Editar un evento propio ({len(archivos_de_eventos_propios())})",
            elegir_y_editar_evento_propio,
        ),
        Opcion("3", "Quitar un evento o cómic", quitar_evento_o_comic),
        Opcion("4", "Ver si cambiaron los eventos en el catálogo", revisar_cambios_eventos),
    ],
)

menu_personajes = Menu(
    "🦸 Personajes",
    [
        Opcion("1", "Sugerir personajes para un evento o cómic (se elige cuáles agregar)", sugerir_personajes),
        Opcion("2", "Rellenar los personajes de todos los eventos y cómics", rellenar_todos_los_personajes),
    ],
    cancelado="↩️  Cancelado (lo ya consultado quedó guardado).",
)

menu_configuracion = Menu(
    "⚙️ Configuración",
    [
        Opcion("1", "Carpeta de notas", cambiar_carpeta_notas),
        Opcion("2", lambda: f"Carpetas de cómics de este PC ({equipo_actual()})", cambiar_carpetas_comics),
        Opcion("3", "Equipos donde leo", ver_equipos),
        Opcion("4", "Actualizar el catálogo desde GitHub", actualizar_catalogo_desde_menu),
        Opcion("5", "Clave de la API de Comic Vine", lambda config: pedir_clave_api(config, forzar=True)),
        Opcion("6", "Restaurar un respaldo", restaurar_respaldo),
        Opcion("7", "Emparejar a mano un archivo sin emparejar", emparejar_a_mano),
        Opcion("8", "Ver o quitar emparejamientos a mano", ver_emparejados),
    ],
)

menu_principal = Menu(
    "📚 Cómics",
    [
        Opcion("1", "Actualizar notas (leídos, archivos nuevos)", generar),
        Opcion("2", "Agregar… (evento, cómic, evento propio)", menu_agregar),
        Opcion("3", "Mi biblioteca (ver, editar, quitar)", menu_biblioteca),
        Opcion("4", "Personajes (Comic Vine)", menu_personajes),
        Opcion("5", "Configuración (carpetas, catálogo, respaldos…)", menu_configuracion),
    ],
    salir="Salir",
)


def main():
    config = leer_config_local()
    try:
        if not preparar(config):
            return
    except (KeyboardInterrupt, EOFError):
        print("↩️  Cancelado.")
        return
    except Exception as error:
        reportar_error(error)
        return
    menu_principal.ejecutar(config)
