
const DATOS = "__DATOS__";

// ================= Utilidades =================
const raiz = dv.container;
const paginaActual = dv.current();
const NOMBRE_PERSONAJE = paginaActual.file.name;
const ESTADO_ENTRE_REFRESCOS = (window.__vistaPersonaje ||= {});
const estadoVista = (ESTADO_ENTRE_REFRESCOS[paginaActual.file.path] ||= { tab: "eventos", pagina: 0, consulta: "" });
const POR_PAGINA = 12;
const ESTILO_CAJA = "background:var(--background-secondary);border:1px solid var(--background-modifier-border);border-radius:12px";

function normalizarTexto(texto) { return (texto || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase(); }
function nombreDeEnlace(enlacePagina) { return (enlacePagina && enlacePagina.path ? enlacePagina.path : String(enlacePagina || "")).replace(/^\[\[|\]\]$/g, "").replace(/\.md$/, "").split("/").pop(); }
function comoLista(valor) { return valor ? [].concat(valor.array ? valor.array() : valor) : []; }
function apareceElPersonaje(paginaComic) { return paginaComic && comoLista(paginaComic.personajes).some(enlacePagina => nombreDeEnlace(enlacePagina) === NOMBRE_PERSONAJE); }

function urlDeImagen(valor) {
  if (!valor) return null;
  const rutaEnlace = (typeof valor === "object" && valor.path) ? valor.path
          : String(valor).replace(/^!?\[\[|\]\]$/g, "").split("|")[0];
  if (!rutaEnlace) return null;
  const archivo = app.metadataCache.getFirstLinkpathDest(rutaEnlace, "");
  return archivo ? app.vault.getResourcePath(archivo) : null;
}
function crearEnlaceInterno(padre, ruta, texto, estilo) {
  const ancla = padre.createEl("a", { text: texto, cls: "internal-link", href: ruta });
  ancla.setAttr("data-href", ruta);
  if (estilo) ancla.setAttr("style", estilo);
  ancla.onclick = (clic) => { clic.preventDefault(); app.workspace.openLinkText(ruta, "", false); };
  return ancla;
}
function abrirArchivo(uriArchivo) {
  try { require("electron").shell.openExternal(uriArchivo); } catch (error) { window.open(uriArchivo); }
}
function dibujarBarraDeProgreso(padre, leidos, total, alto) {
  const fondo = padre.createDiv({ attr: { style: `height:${alto}px;border-radius:${alto / 2}px;background:var(--background-modifier-border);overflow:hidden` } });
  fondo.createDiv({ attr: { style: `height:100%;width:${total ? Math.round(100 * leidos / total) : 0}%;background:var(--interactive-accent)` } });
}
async function alternarLeido(tarea) {
  const archivo = app.vault.getAbstractFileByPath(tarea.path);
  if (!archivo) return;
  const idBloque = tarea.blockId || ((tarea.text || "").match(/\^([\w-]+)\s*$/) || [])[1];
  await app.vault.process(archivo, (texto) => {
    const lineas = texto.split("\n");
    const esTarea = (linea) => /^\s*(>\s*)*- \[[ xX]\]/.test(linea || "");
    let indiceLinea = (typeof tarea.line === "number" && esTarea(lineas[tarea.line]) && (!idBloque || lineas[tarea.line].includes("^" + idBloque))) ? tarea.line : -1;
    if (indiceLinea < 0 && idBloque) indiceLinea = lineas.findIndex(linea => esTarea(linea) && linea.includes("^" + idBloque));
    if (indiceLinea >= 0) lineas[indiceLinea] = /^\s*(>\s*)*- \[ \]/.test(lineas[indiceLinea]) ? lineas[indiceLinea].replace("- [ ]", "- [x]") : lineas[indiceLinea].replace(/- \[[xX]\]/, "- [ ]");
    return lineas.join("\n");
  });
}
function dibujarPaginador(padre, numeroPaginaActual, paginas, irAPagina) {
  if (paginas <= 1) return;
  const navegacion = padre.createDiv({ attr: { style: "display:flex;align-items:center;justify-content:center;gap:12px;margin-top:12px" } });
  const botonAnterior = navegacion.createEl("button", { text: "◀ Anterior" });
  botonAnterior.disabled = numeroPaginaActual === 0;
  botonAnterior.onclick = () => irAPagina(numeroPaginaActual - 1);
  navegacion.createSpan({ text: `Página ${numeroPaginaActual + 1} de ${paginas}`, attr: { style: "font-size:0.85em;color:var(--text-muted)" } });
  const botonSiguiente = navegacion.createEl("button", { text: "Siguiente ▶" });
  botonSiguiente.disabled = numeroPaginaActual >= paginas - 1;
  botonSiguiente.onclick = () => irAPagina(numeroPaginaActual + 1);
}
function textoNumero(tarea) {
  return (tarea.text || "").replace(/\s*·\s*📌.*$/, "").replace(/\[([^\]]+)\]\(<[^>]*>\)/g, "$1").replace(/\s*❌/, "").replace(/\s*\^[\w-]+\s*$/, "").trim();
}
function uriDelNumero(tarea) {
  const coincidencia = (tarea.text || "").match(/\]\(<(file:[^>]+)>\)/);
  return coincidencia ? coincidencia[1] : null;
}
function aniosTexto(intervalo) { return (intervalo && intervalo[0]) ? (intervalo[0] === intervalo[1] ? String(intervalo[0]) : `${intervalo[0]}–${intervalo[1]}`) : ""; }

// ================= Tarjeta «Mi resumen» (el texto vive en la propiedad «resumen» de la nota) =================
function tarjetaResumen(padre) {
  const archivo = app.vault.getAbstractFileByPath(paginaActual.file.path);
  const borradores = (window.__borradorResumen ||= {});                 // lo escrito sin guardar sobrevive si la vista se redibuja
  const tarjeta = padre.createDiv({ attr: { style: ESTILO_CAJA + ";padding:12px 16px;margin-bottom:18px" } });
  const leerResumen = () => String(((app.metadataCache.getFileCache(archivo) || {}).frontmatter || {}).resumen ?? "");
  function mostrar(texto) {
    tarjeta.empty();
    const cabecera = tarjeta.createDiv({ attr: { style: "display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px" } });
    cabecera.createEl("strong", { text: "📝 Mi resumen" });
    cabecera.createEl("button", { text: "✏️ Editar" }).onclick = () => editar(texto);
    if (texto.trim()) dv.el("div", texto, { container: tarjeta });
    else tarjeta.createDiv({ text: "Todavía no escribiste un resumen.", attr: { style: "color:var(--text-muted);font-size:0.9em" } });
  }
  function editar(texto) {
    tarjeta.empty();
    tarjeta.createEl("strong", { text: "📝 Mi resumen" });
    const cuadro = tarjeta.createEl("textarea", { attr: { rows: "8", style: "display:block;width:100%;margin:8px 0;resize:vertical;font-family:inherit" } });
    cuadro.value = texto;
    cuadro.oninput = () => { borradores[archivo.path] = cuadro.value; };
    const botones = tarjeta.createDiv({ attr: { style: "display:flex;gap:8px;justify-content:flex-end" } });
    botones.createEl("button", { text: "Cancelar" }).onclick = () => { delete borradores[archivo.path]; mostrar(leerResumen()); };
    botones.createEl("button", { text: "💾 Guardar", cls: "mod-cta" }).onclick = async () => {
      const nuevo = cuadro.value.replace(/\s+$/, "");
      await app.fileManager.processFrontMatter(archivo, (propiedades) => { propiedades.resumen = nuevo; });
      delete borradores[archivo.path];
      mostrar(nuevo);
    };
    cuadro.focus();
  }
  if (borradores[archivo.path] !== undefined) editar(borradores[archivo.path]);
  else mostrar(leerResumen());
}
tarjetaResumen(raiz);

// ================= Datos =================
let datos = null;
try { datos = JSON.parse(await dv.io.load(DATOS)); } catch (error) { datos = null; }

if (!datos) {
  raiz.createDiv({ text: "⚠️ No encuentro los datos del programa. Elige «Actualizar notas» (opción 1) en el programa para generarlos.", attr: { style: ESTILO_CAJA + ";padding:12px" } });
} else {
  const cacheComic = {};
  function tareasDelEvento(evento) {                                            // los números de un evento, en su orden
    const resultado = [];
    for (const [nota, idBloque] of evento.numeros) {
      if (!cacheComic[nota]) {
        const paginaComic = dv.page(nota);
        const mapa = new Map();
        if (paginaComic) for (const tarea of (paginaComic.file.tasks.array ? paginaComic.file.tasks.array() : [...paginaComic.file.tasks])) {
          const idBloqueTarea = tarea.blockId || ((tarea.text || "").match(/\^([\w-]+)\s*$/) || [])[1];
          if (idBloqueTarea) mapa.set(idBloqueTarea, tarea);
        }
        cacheComic[nota] = mapa;
      }
      const tarea = cacheComic[nota].get(idBloque);
      if (tarea) resultado.push(tarea);
    }
    return resultado;
  }
  const clave = (tarea) => `${tarea.path}#${tarea.line}`;

  // Los eventos y cómics donde aparece
  const lecturasDelPersonaje = [];
  for (const nombre of datos.orden) {
    const evento = datos.eventos[nombre];
    const paginaEvento = dv.page(evento.nota);
    if (!apareceElPersonaje(paginaEvento)) continue;
    const tareas = tareasDelEvento(evento);
    lecturasDelPersonaje.push({ tipo: "evento", ruta: evento.nota, nombre: evento.nombre_visible, textoAnios: aniosTexto(evento.anios_evento), portada: paginaEvento.banner, pagina: paginaEvento, tareas,
                leidos: tareas.filter(tarea => tarea.completed).length, total: evento.numeros.length });
  }
  for (const paginaComic of dv.pages(`"${datos.comics}"`).sort(paginaComic => paginaComic.file.name)) {
    if (!apareceElPersonaje(paginaComic)) continue;
    const tareas = paginaComic.file.tasks.array ? paginaComic.file.tasks.array() : [...paginaComic.file.tasks];
    lecturasDelPersonaje.push({ tipo: "comic", ruta: paginaComic.file.path, nombre: paginaComic.file.name, textoAnios: "", portada: paginaComic.banner, pagina: paginaComic, tareas,
                leidos: tareas.filter(tarea => tarea.completed).length, total: tareas.length });
  }
  const eventos = lecturasDelPersonaje.filter(lectura => lectura.tipo === "evento"), comics = lecturasDelPersonaje.filter(lectura => lectura.tipo === "comic");
  const unicos = new Map();                                          // cada número cuenta una sola vez aunque esté en un evento y en un cómic
  for (const lecturaDelPersonaje of lecturasDelPersonaje) for (const tarea of lecturaDelPersonaje.tareas) unicos.set(clave(tarea), tarea);
  const total = unicos.size;
  const leidos = [...unicos.values()].filter(tarea => tarea.completed).length;

  // El siguiente número por leer: primero lo que está en sus eventos (en el orden de tus eventos), luego sus cómics
  let sig = null;
  for (const lecturaDelPersonaje of lecturasDelPersonaje) {
    const tarea = lecturaDelPersonaje.tareas.find(tarea => !tarea.completed);
    if (tarea) { sig = { tarea, de: lecturaDelPersonaje }; break; }
  }

  // Con quién aparece más
  const juntos = new Map();
  for (const lecturaDelPersonaje of lecturasDelPersonaje) for (const enlacePagina of comoLista(lecturaDelPersonaje.pagina.personajes)) {
    const nombreCompanero = nombreDeEnlace(enlacePagina);
    if (nombreCompanero && nombreCompanero !== NOMBRE_PERSONAJE) juntos.set(nombreCompanero, (juntos.get(nombreCompanero) || 0) + 1);
  }
  const topJuntos = [...juntos.entries()].sort((primero, segundo) => segundo[1] - primero[1]).slice(0, 8);

  // ---- Tarjeta principal
  const porcentaje = total ? Math.round(100 * leidos / total) : 0;
  const tarjetaPrincipal = raiz.createDiv({ attr: { style: ESTILO_CAJA + ";display:flex;gap:18px;padding:16px;align-items:center;flex-wrap:wrap" } });
  const avatar = tarjetaPrincipal.createDiv({ attr: { style: "width:96px;height:96px;min-width:96px;border-radius:50%;overflow:hidden;background:var(--background-modifier-border);display:flex;align-items:center;justify-content:center;font-size:2.4em;border:3px solid var(--interactive-accent)" } });
  const imgPj = urlDeImagen(paginaActual.imagen);
  if (imgPj) avatar.createEl("img", { attr: { src: imgPj, style: "width:100%;height:100%;object-fit:cover;pointer-events:none" } });
  else avatar.setText(NOMBRE_PERSONAJE.charAt(0));
  const columnaInfo = tarjetaPrincipal.createDiv({ attr: { style: "display:flex;flex-direction:column;gap:8px;flex:1;min-width:220px" } });
  columnaInfo.createDiv({ text: "PERSONAJE", attr: { style: "font-size:0.75em;letter-spacing:0.12em;color:var(--text-muted)" } });
  columnaInfo.createDiv({ text: NOMBRE_PERSONAJE, attr: { style: "font-size:1.35em;font-weight:700;line-height:1.2" } });
  if (!lecturasDelPersonaje.length) {
    columnaInfo.createDiv({ text: "Todavía no aparece en ningún evento ni cómic. Agrégalo en la propiedad «personajes» de un evento o cómic (con corchetes dobles: [[" + NOMBRE_PERSONAJE + "]]).",
                     attr: { style: "color:var(--text-muted)" } });
  } else {
    const filaPorcentaje = columnaInfo.createDiv({ attr: { style: "display:flex;align-items:baseline;gap:10px" } });
    filaPorcentaje.createDiv({ text: `${porcentaje}%`, attr: { style: "font-size:1.8em;font-weight:700" } });
    filaPorcentaje.createDiv({ text: `${leidos} de ${total} números leídos`, attr: { style: "color:var(--text-muted)" } });
    dibujarBarraDeProgreso(columnaInfo, leidos, total, 10);
    const chips = columnaInfo.createDiv({ attr: { style: "display:flex;flex-wrap:wrap;gap:6px" } });
    for (const texto of [`⚡ ${eventos.length} evento${eventos.length === 1 ? "" : "s"}`, `📖 ${comics.length} cómic${comics.length === 1 ? "" : "s"}`]) {
      chips.createSpan({ text: texto, attr: { style: "font-size:0.75em;padding:2px 8px;border-radius:10px;background:var(--background-modifier-border)" } });
    }
    if (sig) {
      columnaInfo.createDiv({ text: `▶ Para seguirlo: ${textoNumero(sig.tarea)} — de «${sig.de.nombre}»`, attr: { style: "font-size:0.9em" } });
      const botones = columnaInfo.createDiv({ attr: { style: "display:flex;gap:8px;flex-wrap:wrap;align-items:center" } });
      const uriArchivo = uriDelNumero(sig.tarea);
      if (uriArchivo) {
        const botonLeer = botones.createEl("button", { text: "📖 Leer", cls: "mod-cta" });
        botonLeer.onclick = () => abrirArchivo(uriArchivo);
      }
      const marcar = botones.createEl("button", { text: "✔ Marcar como leído" });
      marcar.onclick = async () => { marcar.disabled = true; marcar.setText("Marcando…"); await alternarLeido(sig.tarea); };
      if (!uriArchivo) botones.createSpan({ text: "❌ No tienes este archivo", attr: { style: "font-size:0.85em;color:var(--text-muted)" } });
    } else {
      columnaInfo.createDiv({ text: "🎉 Ya leíste todo lo que tienes de este personaje", attr: { style: "font-weight:600" } });
    }
  }

  // ---- Aparece junto a
  if (topJuntos.length) {
    raiz.createEl("h2", { text: "🤝 Aparece junto a", attr: { style: "margin-top:1.4em" } });
    const filaCompaneros = raiz.createDiv({ attr: { style: "display:flex;flex-wrap:wrap;gap:14px" } });
    for (const [nombre, veces] of topJuntos) {
      const paginaPersonaje = dv.pages().where(pagina => pagina.file.name === nombre).first();
      const recuadroCompanero = filaCompaneros.createDiv({ attr: { title: `${veces} lectura${veces === 1 ? "" : "s"} en común`, style: "display:flex;flex-direction:column;align-items:center;gap:4px;width:78px;cursor:pointer" } });
      const circuloCompanero = recuadroCompanero.createDiv({ attr: { style: "width:54px;height:54px;border-radius:50%;overflow:hidden;background:var(--background-secondary);display:flex;align-items:center;justify-content:center;font-size:1.3em;border:2px solid var(--interactive-accent)" } });
      const imagen = urlDeImagen(paginaPersonaje && paginaPersonaje.imagen);
      if (imagen) circuloCompanero.createEl("img", { attr: { src: imagen, style: "width:100%;height:100%;object-fit:cover;pointer-events:none" } });
      else circuloCompanero.setText(nombre.charAt(0));
      recuadroCompanero.createDiv({ text: nombre, attr: { style: "font-size:0.75em;text-align:center;line-height:1.2" } });
      recuadroCompanero.createDiv({ text: `${veces}×`, attr: { style: "font-size:0.65em;color:var(--text-muted)" } });
      recuadroCompanero.onclick = () => app.workspace.openLinkText(paginaPersonaje ? paginaPersonaje.file.path : nombre, "", false);
    }
  }

  // ---- Galería de sus eventos y cómics
  if (lecturasDelPersonaje.length) {
    const pestanas = raiz.createDiv({ attr: { style: "display:flex;gap:8px;margin:18px 0 8px;flex-wrap:wrap" } });
    const botonEventos = pestanas.createEl("button", { text: `⚡ Eventos (${eventos.length})` });
    const botonComics = pestanas.createEl("button", { text: `📖 Cómics (${comics.length})` });
    const buscador = raiz.createEl("input", { attr: { type: "search", placeholder: "🔎 Buscar…", style: "width:100%;margin-bottom:8px" } });
    buscador.value = estadoVista.consulta;
    const zonaGaleria = raiz.createDiv();
    const dibujarPagina = () => {
      if (estadoVista.tab === "eventos") { botonEventos.addClass("mod-cta"); botonComics.removeClass("mod-cta"); } else { botonComics.addClass("mod-cta"); botonEventos.removeClass("mod-cta"); }
      zonaGaleria.empty();
      const consulta = normalizarTexto(buscador.value.trim());
      const lecturasFiltradas = (estadoVista.tab === "eventos" ? eventos : comics).filter(lectura => !consulta || normalizarTexto(lectura.nombre).includes(consulta));
      const paginas = Math.max(1, Math.ceil(lecturasFiltradas.length / POR_PAGINA));
      estadoVista.pagina = Math.min(estadoVista.pagina, paginas - 1);
      zonaGaleria.createDiv({ text: lecturasFiltradas.length ? `${lecturasFiltradas.length} resultado${lecturasFiltradas.length === 1 ? "" : "s"}` : "No hay resultados",
                       attr: { style: "font-size:0.8em;color:var(--text-muted);margin-bottom:8px" } });
      const cuadricula = zonaGaleria.createDiv({ attr: { style: "display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:14px" } });
      for (const lectura of lecturasFiltradas.slice(estadoVista.pagina * POR_PAGINA, (estadoVista.pagina + 1) * POR_PAGINA)) {
        const recuadroLectura = cuadricula.createDiv({ attr: { style: "background:var(--background-secondary);border-radius:10px;overflow:hidden;display:flex;flex-direction:column;position:relative" } });
        if (lectura.total && lectura.leidos === lectura.total) recuadroLectura.createDiv({ text: "✅ Completo", attr: { style: "position:absolute;top:6px;left:6px;font-size:0.65em;padding:2px 6px;border-radius:6px;background:var(--background-primary);opacity:0.9" } });
        const contenedorPortada = recuadroLectura.createDiv({ attr: { style: "aspect-ratio:2/3;background:var(--background-modifier-border);display:flex;align-items:center;justify-content:center;font-size:2em;cursor:pointer" } });
        const imagen = urlDeImagen(lectura.portada);
        if (imagen) contenedorPortada.createEl("img", { attr: { src: imagen, style: "width:100%;height:100%;object-fit:cover;pointer-events:none" } });
        else contenedorPortada.setText(lectura.tipo === "evento" ? "⚡" : "📚");
        contenedorPortada.onclick = () => app.workspace.openLinkText(lectura.ruta, "", false);
        const pieTarjeta = recuadroLectura.createDiv({ attr: { style: "padding:6px 8px 8px;display:flex;flex-direction:column;gap:4px" } });
        crearEnlaceInterno(pieTarjeta, lectura.ruta, lectura.nombre, "font-size:0.8em;font-weight:600;line-height:1.25");
        if (lectura.textoAnios) pieTarjeta.createDiv({ text: "📅 " + lectura.textoAnios, attr: { style: "font-size:0.7em;color:var(--text-muted)" } });
        const filaBarra = pieTarjeta.createDiv({ attr: { style: "display:flex;align-items:center;gap:6px;font-size:0.75em;color:var(--text-muted)" } });
        const fondo = filaBarra.createDiv({ attr: { style: "flex:1;height:6px;border-radius:3px;background:var(--background-modifier-border);overflow:hidden" } });
        fondo.createDiv({ attr: { style: `height:100%;width:${lectura.total ? Math.round(100 * lectura.leidos / lectura.total) : 0}%;background:var(--interactive-accent)` } });
        filaBarra.createSpan({ text: `${lectura.leidos}/${lectura.total}` });
      }
      dibujarPaginador(zonaGaleria, estadoVista.pagina, paginas, (numeroPagina) => { estadoVista.pagina = numeroPagina; dibujarPagina(); });
    };
    botonEventos.onclick = () => { estadoVista.tab = "eventos"; estadoVista.pagina = 0; dibujarPagina(); };
    botonComics.onclick = () => { estadoVista.tab = "comics"; estadoVista.pagina = 0; dibujarPagina(); };
    buscador.oninput = () => { estadoVista.consulta = buscador.value; estadoVista.pagina = 0; dibujarPagina(); };
    if (estadoVista.tab === "eventos" && !eventos.length) estadoVista.tab = "comics";
    dibujarPagina();
  }
}
