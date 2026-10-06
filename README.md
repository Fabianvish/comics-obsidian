# 📚 Cómics para Obsidian

Proyecto personal hecho para llevar lecturas de cómics en [Obsidian](https://obsidian.md).
Lo comparto por si a alguien le sirve, pero es un programa hecho a mi medida: puede tener errores
y cosas que se podrían hacer mejor.

Qué hace:

- Descarga un **catálogo de órdenes de lectura** (eventos como *Civil War*, *Secret Wars*…) desde
  [CBL-ReadingLists](https://github.com/DieselTech/CBL-ReadingLists).
- Crea una nota por **evento**, por **cómic** y por **personaje**, con casillas para marcar lo leído.
- Busca los **archivos de cómics** (`.cbr`, `.cbz`, `.cb7`, `.pdf`), los empareja con cada número,
  saca las **portadas** y enlaza cada número a su archivo.
- Opcionalmente, consulta **Comic Vine** para sugerir los personajes de cada evento o cómic.
- Lo uso en **Windows** y **WSL**; también debería funcionar en **Linux** y macOS. El mismo vault
  se puede usar desde varios PC (por ejemplo, sincronizado con OneDrive).

Es un programa de consola, con menús numerados: **Enter** acepta y **Esc** cancela en cualquier pregunta.

## Índice

1. [Qué se necesita](#requisitos)
2. [Paso 1: preparar Obsidian](#paso-1)
3. [Paso 2: instalar Python y los extras](#paso-2)
4. [Paso 3: obtener el programa](#paso-3)
5. [Paso 4: ejecutar](#paso-4)
6. [Menú](#menu)
7. [Clave de Comic Vine (opcional)](#comic-vine)
8. [Qué crea en el vault](#vault)
9. [Usar el mismo vault en varios PC](#varios-pc)
10. [Nombres de archivos de cómics](#nombres)
11. [Problemas frecuentes](#problemas)
12. [Variables de entorno (avanzado)](#variables)

---

<a id="requisitos"></a>

## ✅ Qué se necesita

### Obligatorio

| Qué | Para qué |
|---|---|
| **Python 3.8 o superior** | Ejecutar el programa. No necesita librerías externas. |
| **Obsidian** | Ver y usar las notas. |
| Plugin **Dataview** (con *Enable JavaScript Queries* activado) | Las notas muestran sus vistas (progreso, portadas, filtros) con bloques `dataviewjs`. |
| Conexión a internet (la primera vez) | Descargar el catálogo (~12 MB). |

### Opcional (recomendado)

| Qué | Para qué |
|---|---|
| **Pillow** (`pip install pillow`) | Achica las portadas a JPG de 600×900. Sin Pillow se guarda la imagen original (pesa más). |
| **unrar** o **7-Zip** (`7z`, `7zz` o `7za`) | Sacar la portada de archivos `.cbr` y `.cb7`. Los `.cbz` funcionan sin nada extra. Los `.pdf` no tienen portada. |
| Plugin **Pixel Banner** | Muestra la portada como banner (propiedad `banner` de las notas). |
| Plugin **Extended Graph** | Usa la propiedad `imagen` de las notas de evento para mostrar imágenes en el grafo. |
| Clave gratuita de **Comic Vine** | Sugerir personajes (menú *Personajes*). |

---

<a id="paso-1"></a>

## 🧩 Paso 1: preparar Obsidian

1. Instalar Obsidian y abrir (o crear) un vault.
2. Ir a **Configuración → Complementos de la comunidad** (*Community plugins*) y activarlos si está en modo restringido.
3. **Explorar** → buscar **Dataview** → **Instalar** → **Activar**.
4. Abrir las opciones de Dataview y activar **Enable JavaScript Queries**
   (y también **Enable Inline JavaScript Queries**, por si acaso).
5. (Opcional) Instalar **Pixel Banner** y **Extended Graph** de la misma forma.

> Si las notas muestran el código ```` ```dataviewjs ```` en vez de las vistas, falta el paso 4.

---

<a id="paso-2"></a>

## 💻 Paso 2: instalar Python y los extras

### Windows

1. Instalar Python desde <https://www.python.org/downloads/> (o desde Microsoft Store).
   En el instalador, marcar **“Add python.exe to PATH”**.
2. Comprobar en PowerShell o Símbolo del sistema:
   ```powershell
   python --version
   ```
3. (Opcional) Pillow:
   ```powershell
   python -m pip install pillow
   ```
4. (Opcional) Para portadas de `.cbr`/`.cb7`: instalar [7-Zip](https://www.7-zip.org/) y agregar
   `C:\Program Files\7-Zip` al **PATH** (Configuración → Sistema → Acerca de → Configuración avanzada →
   Variables de entorno → `Path` → Editar → Nuevo). O con winget:
   ```powershell
   winget install 7zip.7zip
   ```
   Comprobar con `7z` en una consola nueva.

> **Usar Windows Terminal o PowerShell** para que se vean bien los emojis de los menús.

### WSL (Ubuntu / Debian en Windows)

1. Si no está WSL: en PowerShell como administrador, `wsl --install` y reiniciar.
2. En la terminal de WSL:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pil unrar p7zip-full
   ```
   (`unrar` está en el repositorio *multiverse*; si no lo encuentra, basta con `p7zip-full` o `7zip`.)
3. Las rutas de Windows se pueden escribir tal cual (`C:\Users\...`): el programa las convierte a `/mnt/c/...`.
4. Los enlaces a los archivos de cómics se guardan como `file:///C:/...`, así que se abren desde
   **Obsidian en Windows** aunque el programa corra en WSL.

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

Pillow también se puede instalar con `python3 -m pip install --user pillow` (o en un entorno virtual).

### macOS

```bash
brew install python 7zip   # o: brew install sevenzip
python3 -m pip install pillow
```

---

<a id="paso-3"></a>

## 📥 Paso 3: obtener el programa

Copiar o clonar esta carpeta donde se prefiera, por ejemplo:

- Windows: `C:\Users\TuUsuario\Scripts\comics-obsidian`
- WSL / Linux: `~/Scripts/comics-obsidian`

Debe quedar así:

```
comics-obsidian/
├── comics.py        ← se ejecuta este
├── programa/        ← el código (un módulo por tema)
└── vistas/          ← las vistas de Obsidian (JavaScript para Dataview)
```

---

<a id="paso-4"></a>

## ▶️ Paso 4: ejecutar

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

### La primera vez

1. **Carpeta para las notas**: la ruta del vault o de una carpeta dentro de él
   (ej.: `C:\Users\TuUsuario\OneDrive\Obsidian\MiVault\Comics`). Si no existe, se crea.
   Si no encuentra un vault (carpeta `.obsidian`) avisa, pero sigue igual.
2. **Carpeta de cómics** de este PC: donde están los archivos. Se puede responder `N` (ninguna por ahora)
   y agregarlas después. Se pueden tener varias.
3. Al usar el catálogo por primera vez, se descarga (~12 MB) y se ordena.

---

<a id="menu"></a>

## 🗂️ Menú

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
| **Agregar** | Evento del catálogo · Seguir un cómic · Crear un evento propio · Copiar un evento para editarlo · Importar un orden de lectura (`.cbl`, carpeta o enlace de GitHub) |
| **Mi biblioteca** | Ver eventos y cómics · Editar un evento propio · Quitar · Ver si cambiaron los eventos en el catálogo |
| **Personajes** | Sugerir personajes para un evento o cómic · Rellenar los de todos |
| **Configuración** | Carpeta de notas · Carpetas de cómics de este PC · Equipos · Actualizar catálogo · Clave de Comic Vine · Restaurar respaldo · Emparejar archivos a mano |

### Flujo de uso típico

1. **Agregar → Evento del catálogo** y buscar, por ejemplo, `civil war`.
2. Abrir Obsidian: aparecen las notas en `Eventos/` y `Cómics/`, y la página de inicio **Mis lecturas** (progreso y el siguiente número por leer).
3. Marcar las casillas de lo leído en Obsidian.
4. Volver a ejecutar **1. Actualizar notas** cada vez que se agreguen archivos o se quiera sincronizar lo leído
   entre eventos y cómics.

---

<a id="comic-vine"></a>

## 🦸 Clave de Comic Vine (opcional)

1. Crear una cuenta gratuita en <https://comicvine.gamespot.com> (es una cuenta de GameSpot).
2. Entrar a <https://comicvine.gamespot.com/api> y copiar la clave.
3. En el programa: **Configuración → Clave de la API de Comic Vine** (o se pide sola al usar *Personajes*).

La clave se guarda solo en `comics_config.json` de este computador; no se sube al vault.
La API permite ~200 consultas por hora: el programa respeta ese límite y guarda lo consultado,
así que si se corta se puede seguir después.

---

<a id="vault"></a>

## 📁 Qué crea en el vault

```
<carpeta de notas>/
├── Mis lecturas.md           página de inicio: progreso y siguiente número
├── Revisar mi biblioteca.md  qué números tienes y cuáles faltan
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

Las notas tienen secciones propias (ej. **📝 Mi resumen**) que el programa respeta al actualizar.
**Los archivos de cómics nunca se modifican**: solo se leen.

En la carpeta del programa quedan:

| Archivo | Contenido |
|---|---|
| `comics_config.json` | Dónde están las notas en este PC y la clave de Comic Vine. |
| `catalogo.zip`, `catalogo.json` | El catálogo descargado y su índice. |
| `respaldos/` | Últimos 10 respaldos (`.zip`) de las notas y del estado. |
| `comics_errores.log` | Detalle técnico de errores, si los hay. |

Todos están en `.gitignore`.

---

<a id="varios-pc"></a>

## 🔄 Usar el mismo vault en varios PC (o Windows + WSL)

- El estado vive en `_programa/` **dentro del vault**, así que viaja con OneDrive, Syncthing, etc.
- Cada PC guarda sus propias carpetas de cómics en `_programa/equipos.json`. La primera vez en un PC nuevo,
  el programa ofrece reutilizar las rutas de otro equipo.
- **Windows y WSL en el mismo PC cuentan como el mismo equipo**: las rutas se guardan como `C:\...`
  y se traducen a `/mnt/c/...` (y al revés) automáticamente.
- Se puede compartir también la carpeta del programa: `comics_config.json` guarda la carpeta de notas por equipo.

---

<a id="nombres"></a>

## 📄 Nombres de archivos de cómics

El emparejamiento funciona mejor con nombres del estilo:

```
Civil War 001 (2006).cbz
Amazing Spider-Man #532 (2006) (Digital).cbr
X-Men_05 (1991).pdf
```

Es decir: **nombre de la serie + número**, y si es posible el **año entre paréntesis**.
Lo que esté entre `()`, `[]` o `{}` se ignora, salvo el año. Si algo no se empareja,
usar **Configuración → Emparejar a mano un archivo sin emparejar**.

---

<a id="problemas"></a>

## 🛠️ Problemas frecuentes

| Problema | Solución |
|---|---|
| `python` no se reconoce (Windows) | Reinstalar Python marcando *Add to PATH*, o usar `py comics.py`. |
| Las notas muestran código `dataviewjs` | Instalar Dataview y activar *Enable JavaScript Queries*. Reiniciar Obsidian. |
| No aparecen portadas de `.cbr` | Instalar `unrar` o 7-Zip y verificar que estén en el PATH. |
| Portadas muy pesadas | Instalar Pillow y volver a *Actualizar notas* (solo afecta portadas nuevas). |
| «No se encuentra la carpeta de notas» | El disco u OneDrive no está disponible. Conectarlo, o elegir otra carpeta (opción 6). |
| Los enlaces a archivos no abren desde WSL | Abrir el vault con Obsidian **en Windows**; los enlaces son `file:///C:/...`. |
| Emojis o tildes raros en la consola | Usar Windows Terminal; en Linux, una terminal con UTF-8. |
| Algo se rompió en las notas | **Configuración → Restaurar un respaldo**. |
| Otro error | Ver `comics_errores.log` en la carpeta del programa. |

---

<a id="variables"></a>

## ⚙️ Variables de entorno (avanzado)

| Variable | Por defecto | Uso |
|---|---|---|
| `COMICS_API_URL` | `https://comicvine.gamespot.com/api` | URL de la API de Comic Vine. |
| `COMICS_API_PAUSA` | `1.1` | Segundos de espera entre consultas a la API. |
