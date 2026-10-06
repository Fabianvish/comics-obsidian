"""Constantes y ubicaciones de archivos del programa."""

import os
import platform
from pathlib import Path


CARPETA_PROGRAMA = Path(__file__).resolve().parent.parent  # carpeta que contiene a comics.py


ARCHIVO_CONFIG_LOCAL = CARPETA_PROGRAMA / "comics_config.json"


ARCHIVO_REGISTRO_ERRORES = CARPETA_PROGRAMA / "comics_errores.log"


CLAVES_LOCALES = ("notas", "comics", "clave_api")


ARCHIVO_CATALOGO_ZIP = CARPETA_PROGRAMA / "catalogo.zip"


ARCHIVO_INDICE_CATALOGO = CARPETA_PROGRAMA / "catalogo.json"


URL_REPOSITORIO_ZIP = "https://codeload.github.com/DieselTech/CBL-ReadingLists/zip/refs/heads/main"


CARPETA_VISTAS = CARPETA_PROGRAMA / "vistas"  # las vistas de Obsidian (JavaScript) viven en archivos aparte


VERSION_INDICE = 3


URL_API = os.environ.get("COMICS_API_URL", "https://comicvine.gamespot.com/api")


PAUSA_ENTRE_PETICIONES = float(
    os.environ.get("COMICS_API_PAUSA", "1.1")
)  # segundos entre peticiones (límite por segundo)


PETICIONES_POR_HORA = 195  # el límite oficial es 200 por recurso por hora


EXTENSIONES_COMIC = {".cbr", ".cbz", ".cb7", ".pdf"}


MARCA_INICIO_NUMEROS, MARCA_FIN_NUMEROS = "<!-- numeros:inicio -->", "<!-- numeros:fin -->"


CARPETA_RESPALDOS = CARPETA_PROGRAMA / "respaldos"


MAXIMO_RESPALDOS = 10


EXTENSIONES_IMAGEN = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


ES_WSL = "microsoft" in platform.uname().release.lower()


ORDEN_PREFERIDO_DE_FUENTES = ["CBRO", "Marvel Guides", "Official", "CBH", "CBT", "LoCG", "Community"]


# Carpetas del vault que maneja el programa (relativas a la carpeta de notas)
CARPETA_NOTAS_EVENTOS = "Eventos"  # salvo que un evento propio indique otra
CARPETA_NOTAS_COMICS = "Cómics"
CARPETA_NOTAS_PERSONAJES = "Personajes"
CARPETA_VISTAS_VAULT = "_vistas"  # copia de las vistas de Obsidian y sus datos
CARPETA_ESTADO = "_programa"  # lo que viaja con el vault: eventos, leídos, equipos
CARPETA_PORTADAS = "Imagenes/portadas"
CARPETA_ARCHIVADAS = "Archivadas"
CARPETAS_RESERVADAS = {  # nombres que un evento propio no puede usar como carpeta de su nota
    nombre.lower()
    for nombre in (CARPETA_NOTAS_COMICS, "comics", CARPETA_NOTAS_PERSONAJES, CARPETA_VISTAS_VAULT, CARPETA_ARCHIVADAS, CARPETA_ESTADO)
}


RESULTADOS_POR_PAGINA = 15  # líneas por página en las listas largas (se navega con S = siguiente y A = anterior)
