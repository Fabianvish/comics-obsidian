# 📚 Cómics para Obsidian

Proyecto personal hecho para llevar lecturas de cómics en [Obsidian](https://obsidian.md).

Qué hace:

- Descarga un catálogo de órdenes de lectura (eventos como *Civil War* o *Secret Wars*) desde
  [CBL-ReadingLists](https://github.com/DieselTech/CBL-ReadingLists).
- Crea una nota por evento, por cómic y por personaje, con casillas para marcar lo leído.
- Busca los archivos de cómics (`.cbr`, `.cbz`, `.cb7`, `.pdf`), los empareja con cada número,
  extrae las portadas y enlaza cada número a su archivo.
- Opcionalmente, consulta Comic Vine para sugerir los personajes de cada evento o cómic.
- Probado en Windows y WSL; debería funcionar también en Linux y macOS. El mismo vault
  se puede usar desde varios PC (por ejemplo, sincronizado con OneDrive).

Es un programa de consola con menús numerados: Enter acepta y Esc cancela en cualquier pregunta.

## Índice

1. [Requisitos](#requisitos)
2. [Paso 1: preparar Obsidian](#paso-1)
3. [Paso 2: instalar Python y los extras](#paso-2)
4. [Paso 3: obtener el programa](#paso-3)
5. [Paso 4: ejecutar](#paso-4)
6. [Menú](#menu)
7. [Clave de Comic Vine (opcional)](#comic-vine)
8. [Archivos que se crean](#vault)
9. [Uso en varios PC](#varios-pc)
10. [Nombres de archivos de cómics](#nombres)
11. [Problemas frecuentes](#problemas)
12. [Variables de entorno](#variables)
13. [Agradecimientos](#agradecimientos)

---

<a id="requisitos"></a>

## Requisitos

### Obligatorios

| Requisito | Uso |
|---|---|
| Python 3.8 o superior | Ejecutar el programa. No necesita librerías externas. |
| Obsidian | Ver y usar las notas. |
| Plugin Dataview, con *Enable JavaScript Queries* activado | Mostrar las vistas de las notas (progreso, portadas, filtros), escritas como bloques `dataviewjs`. |
| Conexión a internet la primera vez | Descargar el catálogo (unos 12 MB). |

### Opcionales

| Requisito | Uso |
|---|---|
| Pillow | Reducir las portadas a JPG de 600×900. Sin Pillow se guarda la imagen original, que pesa más. |
| unrar o 7-Zip (`7z`, `7zz` o `7za`) | Extraer la portada de archivos `.cbr` y `.cb7`. Los `.cbz` no necesitan nada extra; los `.pdf` no tienen portada. |
| Plugin Pixel Banner | Mostrar la portada como banner (propiedad `banner` de las notas). |
| Plugin Extended Graph | Mostrar imágenes en el grafo (propiedad `imagen` de las notas de evento). |
| Clave gratuita de Comic Vine | Sugerir personajes (menú *Personajes*). |

---

<a id="paso-1"></a>

## Paso 1: preparar Obsidian

1. Instalar Obsidian y abrir o crear un vault.
2. En **Configuración → Complementos de la comunidad** (*Community plugins*), activar los complementos
   si está en modo restringido.
3. **Explorar** → buscar **Dataview** → **Instalar** → **Activar**.
4. En las opciones de Dataview, activar **Enable JavaScript Queries**.
5. Opcional: instalar **Pixel Banner** y **Extended Graph** de la misma forma.

> Si las notas muestran el código ```` ```dataviewjs ```` en vez de las vistas, falta el paso 4.

---

<a id="paso-2"></a>

## Paso 2: instalar Python y los extras

### Windows

1. Instalar Python desde <https://www.python.org/downloads/> o desde Microsoft Store.
   En el instalador, marcar **Add python.exe to PATH**.
2. Comprobar en PowerShell o en el Símbolo del sistema:
   ```powershell
   python --version
   ```
3. Opcional, Pillow:
   ```powershell
   python -m pip install pillow
   ```
4. Opcional, para portadas de `.cbr` y `.cb7`: instalar [7-Zip](https://www.7-zip.org/) y agregar
   `C:\Program Files\7-Zip` al PATH (Configuración → Sistema → Acerca de → Configuración avanzada del sistema →
   Variables de entorno → `Path` → Editar → Nuevo). También se puede instalar con winget:
   ```powershell
   winget install 7zip.7zip
   ```
   Comprobar con `7z` en una consola nueva.

> Se recomienda Windows Terminal o PowerShell para que los emojis de los menús se vean bien.

### WSL (Ubuntu o Debian en Windows)

1. Si WSL no está instalado: en PowerShell como administrador, ejecutar `wsl --install` y reiniciar.
2. En la terminal de WSL:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pil unrar p7zip-full
   ```
   `unrar` está en el repositorio *multiverse*; si no aparece, basta con `p7zip-full` o `7zip`.
3. Las rutas de Windows se pueden escribir tal cual (`C:\Users\...`); el programa las convierte a `/mnt/c/...`.
4. Los enlaces a los archivos de cómics se guardan como `file:///C:/...`, por lo que se abren desde
   Obsidian en Windows aunque el programa se ejecute en WSL.

### Linux

Debian / Ubuntu:
```bash
sudo apt install python3 python3-pil unrar p7zip-full
```
Fedora:
```bash
sudo dnf install python3 python3-pillow p7zip p7zip-plugins
```
Arch:
```bash
sudo pacman -S python python-pillow unrar 7zip
```

Pillow también se puede instalar con `python3 -m pip install --user pillow` o en un entorno virtual.

### macOS

```bash
brew install python sevenzip
python3 -m pip install pillow
```

---

<a id="paso-3"></a>

## Paso 3: obtener el programa

Copiar o clonar esta carpeta en cualquier ubicación, por ejemplo:

- Windows: `C:\Users\TuUsuario\Scripts\comics-obsidian`
- WSL / Linux: `~/Scripts/comics-obsidian`

Estructura:

```
comics-obsidian/
├── comics.py        ← punto de entrada
├── programa/        ← código, un módulo por tema
└── vistas/          ← vistas de Obsidian (JavaScript para Dataview)
```

---

<a id="paso-4"></a>

## Paso 4: ejecutar

Windows:
```powershell
cd C:\Users\TuUsuario\Scripts\comics-obsidian
python comics.py
```

WSL / Linux / macOS:
```bash
cd ~/Scripts/comics-obsidian
python3 comics.py
```

### Primera ejecución

1. **Carpeta para las notas**: la ruta del vault o de una carpeta dentro de él
   (ej.: `C:\Users\TuUsuario\OneDrive\Obsidian\MiVault\Comics`). Si no existe, se crea.
   Si no hay un vault (carpeta `.obsidian`) en esa ruta, el programa avisa y continúa.
2. **Carpeta de cómics** de este PC: donde están los archivos. Se puede responder `N` (ninguna por ahora)
   y agregarla después. Se admiten varias carpetas.
3. La primera vez que se usa el catálogo, se descarga (unos 12 MB) y se indexa.

---

<a id="menu"></a>

## Menú

```
📚 Cómics
 1. Actualizar notas (leídos, archivos nuevos)
 2. Agregar… (evento, cómic, evento propio)
 3. Mi biblioteca (ver, editar, quitar)
 4. Personajes (Comic Vine)
 5. Configuración (carpetas, catálogo, respaldos…)
```

| Menú | Opciones |
|---|---|
| Agregar | Evento del catálogo · Seguir un cómic · Crear un evento propio · Copiar un evento para editarlo · Importar un orden de lectura (`.cbl`, carpeta o enlace de GitHub) |
| Mi biblioteca | Ver eventos y cómics · Editar un evento propio · Quitar · Ver si cambiaron los eventos en el catálogo |
| Personajes | Sugerir personajes para un evento o cómic · Rellenar los de todos |
| Configuración | Carpeta de notas · Carpetas de cómics de este PC · Equipos · Actualizar catálogo · Clave de Comic Vine · Restaurar respaldo · Emparejar archivos a mano |

### Uso típico

1. **Agregar → Evento del catálogo** y buscar, por ejemplo, `civil war`.
2. En Obsidian aparecen las notas en `Eventos/` y `Cómics/`, y la página de inicio **Mis lecturas**
   (progreso y siguiente número por leer).
3. Marcar en Obsidian las casillas de lo leído.
4. Ejecutar **1. Actualizar notas** al agregar archivos o para sincronizar lo leído entre eventos y cómics.

---

<a id="comic-vine"></a>

## Clave de Comic Vine (opcional)

1. Crear una cuenta gratuita en <https://comicvine.gamespot.com> (es una cuenta de GameSpot).
2. Entrar a <https://comicvine.gamespot.com/api> y copiar la clave.
3. En el programa: **Configuración → Clave de la API de Comic Vine**. También se pide al usar *Personajes*.

La clave se guarda solo en `comics_config.json` de ese computador y no se sube al vault.
La API permite unas 200 consultas por hora; el programa respeta ese límite y guarda lo consultado,
así que se puede continuar más tarde si se interrumpe.

---

<a id="vault"></a>

## Archivos que se crean

En el vault:

```
<carpeta de notas>/
├── Mis lecturas.md           página de inicio: progreso y siguiente número
├── Revisar mi biblioteca.md  números disponibles y faltantes
├── Eventos/                  notas de cada evento
├── Cómics/                   notas de cada cómic (serie)
├── Personajes/               notas de personajes
├── Imagenes/portadas/        portadas extraídas de los archivos
├── _vistas/                  copia de las vistas de Dataview y sus datos
└── _programa/                estado que viaja con el vault
    ├── listas/               eventos agregados
    ├── leidos.json           historial de leídos
    ├── estado.json           configuración portable
    └── equipos.json          carpetas de cómics de cada PC
```

Las secciones propias de las notas (ej. **📝 Mi resumen**) se conservan al actualizar.
Los archivos de cómics nunca se modifican; solo se leen.

En la carpeta del programa:

| Archivo | Contenido |
|---|---|
| `comics_config.json` | Ubicación de las notas en cada PC y clave de Comic Vine. |
| `catalogo.zip`, `catalogo.json` | Catálogo descargado y su índice. |
| `respaldos/` | Últimos 10 respaldos (`.zip`) de las notas y del estado. |
| `comics_errores.log` | Detalle técnico de los errores, si los hay. |

Todos están en `.gitignore`.

---

<a id="varios-pc"></a>

## Uso en varios PC (o en Windows y WSL)

- El estado se guarda en `_programa/`, dentro del vault, por lo que se sincroniza con OneDrive, Syncthing, etc.
- Cada PC guarda sus carpetas de cómics en `_programa/equipos.json`. La primera vez en un PC nuevo,
  el programa ofrece reutilizar las rutas de otro equipo.
- Windows y WSL en el mismo PC cuentan como un solo equipo: las rutas se guardan como `C:\...`
  y se traducen a `/mnt/c/...` (y al revés) automáticamente.
- La carpeta del programa también se puede compartir: `comics_config.json` guarda la carpeta de notas de cada equipo.

---

<a id="nombres"></a>

## Nombres de archivos de cómics

El emparejamiento funciona mejor con nombres como:

```
Civil War 001 (2006).cbz
Amazing Spider-Man #532 (2006) (Digital).cbr
X-Men_05 (1991).pdf
```

Es decir: nombre de la serie, número y, si es posible, año entre paréntesis.
Lo que esté entre `()`, `[]` o `{}` se ignora, salvo el año. Los archivos que no se emparejen
se pueden asignar en **Configuración → Emparejar a mano un archivo sin emparejar**.

---

<a id="problemas"></a>

## Problemas frecuentes

| Problema | Solución |
|---|---|
| `python` no se reconoce (Windows) | Reinstalar Python marcando *Add to PATH*, o usar `py comics.py`. |
| Las notas muestran código `dataviewjs` | Instalar Dataview, activar *Enable JavaScript Queries* y reiniciar Obsidian. |
| No aparecen portadas de `.cbr` | Instalar `unrar` o 7-Zip y verificar que estén en el PATH. |
| Portadas muy pesadas | Instalar Pillow y volver a ejecutar *Actualizar notas* (solo afecta a las portadas nuevas). |
| «No se encuentra la carpeta de notas» | El disco u OneDrive no está disponible. Conectarlo o elegir otra carpeta (opción 6). |
| Los enlaces a archivos no abren desde WSL | Abrir el vault con Obsidian en Windows; los enlaces son `file:///C:/...`. |
| Emojis o tildes incorrectos en la consola | Usar Windows Terminal; en Linux, una terminal con UTF-8. |
| Notas dañadas | **Configuración → Restaurar un respaldo**. |
| Otro error | Revisar `comics_errores.log` en la carpeta del programa. |

---

<a id="variables"></a>

## Variables de entorno

| Variable | Valor por defecto | Uso |
|---|---|---|
| `COMICS_API_URL` | `https://comicvine.gamespot.com/api` | URL de la API de Comic Vine. |
| `COMICS_API_PAUSA` | `1.1` | Segundos de espera entre consultas a la API. |

---

<a id="agradecimientos"></a>

## Agradecimientos

- [CBL-ReadingLists](https://github.com/DieselTech/CBL-ReadingLists), de DieselTech: recopilación de órdenes
  de lectura que se usa como catálogo.
- Autores originales de esas listas, entre ellos [CBRO](https://comicbookreadingorders.com),
  [CMRO](https://cmro.travis-starnes.com), [Comic Book Herald](https://www.comicbookherald.com),
  [Comic Book Treasury](https://www.comicbooktreasury.com) y [Marvel Guides](https://marvelguides.com).
- [Comic Vine](https://comicvine.gamespot.com): datos de personajes, obtenidos mediante su API.
- [Obsidian](https://obsidian.md) y el plugin [Dataview](https://github.com/blacksmithgu/obsidian-dataview).
