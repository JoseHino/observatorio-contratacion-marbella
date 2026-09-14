"""Descarga los documentos que el Ayuntamiento publica en su perfil del
contratante de la PLACSP.

FUENTE UNICA del observatorio. No son los ficheros de datos abiertos: son los
documentos que el propio Ayuntamiento cuelga en la pestana "Documentos" de su
perfil, que es lo que exige el articulo 63 de la LCSP:

  * Listado Anual de Contratos celebrados  -> indicador n 48  (contratos mayores)
  * Relacion de Modificados                -> indicador n 50
  * Relaciones trimestrales y anuales de contratos menores

Guarda cada PDF en _raw/perfil/ y un inventario en _raw/perfil/inventario.json
con el titulo, la fecha de publicacion y la URL de descarga, para que siempre
se pueda rastrear de donde sale cada cifra.
"""
import json
import os
import pathlib
import re
import sys
import unicodedata

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEST = ROOT / "_raw" / "perfil"
DEST.mkdir(parents=True, exist_ok=True)

NIF = "P2906900B"
PERFIL = "https://contrataciondelestado.es/wps/portal/perfilContratante"
PRE = "viewns_Z7_AVEQAI930GRPE02BR764FO30G0_:listaperfiles:"

# El listado de documentos vive en divs, no en una tabla: cada fila es un
# div.flex-inline-xxs con titulo, enlace de descarga y fecha de publicacion.
JS_FILAS = """() => {
  const filas = [];
  document.querySelectorAll("div[id^='epigrafe_']").forEach(ep => {
    ep.querySelectorAll("div.flex-inline-xxs").forEach(f => {
      const cols = [...f.children];
      const titulo = (cols[0]?.textContent || '').trim();
      const a = f.querySelector("a[id^='enlaceDescarga']");
      const fecha = (cols[2]?.textContent || '').trim();
      if (titulo && a) filas.push({titulo, fecha, url: a.href});
    });
  });
  return filas;
}"""


def clase(titulo):
    """Que es cada documento. Lo que no encaja se ignora: decretos de mesa,
    convenios, graficos... no son datos de contratacion."""
    t = unicodedata.normalize("NFKD", titulo.upper())
    t = "".join(c for c in t if not unicodedata.combining(c))
    if "INDICADOR" in t and "48" in t:
        return "mayores"
    if "INDICADOR" in t and "50" in t or "MODIFICADOS" in t:
        return "modificados"
    # "LISTADO COMPLEMENTARIO 2º TRIMESTRE 23" no dice "MENORES" en ninguna
    # parte, y es una relacion de menores: sin esto se perdia entera.
    if "MENORES" in t or "TRIMESTRE" in t:
        return "menores"
    return None


def anio(titulo):
    """Ejercicio al que se refiere el documento, no el de su publicacion.

    Hay que quitar antes el numero de indicador: "Indicador N 48" colandose
    como año daba 2048. Y los titulos abrevian el cierre de tres maneras:
    "al 31/12/2021", "a 31_12_24" y "durante el 2019".
    """
    t = titulo.replace("_", " ").replace("-", " ").replace("/", " ")
    t = re.sub(r"(?i)indicador\s*n[\u00ba\u00b0o]?\s*\d+", " ", t)
    t = re.sub(r"(?i)n[\u00ba\u00b0]\s*\d+", " ", t)

    # El cierre del ejercicio manda sobre cualquier otro numero del titulo.
    m = re.search(r"(?<!\d)31\s+12\s+(\d{2,4})(?!\d)", t)
    if m:
        v = m.group(1)
        return int(v) if len(v) == 4 else 2000 + int(v)

    m = re.search(r"(?<!\d)(20\d{2})(?!\d)", t)
    if m:
        return int(m.group(1))

    # "MENORES 25" al final, ya sin numeros de indicador.
    m = re.search(r"(?<!\d)(\d{2})\s*$", t.strip())
    return 2000 + int(m.group(1)) if m else None


def trimestre(titulo):
    m = re.search(r"([1-4])\s*[ºªO]?\s*(?:ER|er)?\s*TRIMESTRE", titulo.upper())
    return int(m.group(1)) if m else None


def slug(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")[:70]


def id_css(sufijo):
    """El portal usa ids de JSF con dos puntos, que hay que escapar en CSS."""
    return "#" + (PRE + sufijo).replace(":", "\\:")


def abrir_documentos(pg):
    """Busca el perfil por NIF y deja abierta la pestana Documentos.

    Nada de esperas por reloj: el portal responde en menos de un segundo desde
    aqui y en diez desde un runner, asi que se espera a cada elemento. Devuelve
    las filas de documentos ya leidas.
    """
    pg.goto(PERFIL, wait_until="domcontentloaded", timeout=120000)
    pg.wait_for_selector(id_css("inputTextNif"), timeout=60000)
    pg.fill(id_css("inputTextNif"), NIF)
    pg.click(id_css("botonbuscar"))

    enlace = pg.get_by_text("Junta de Gobierno del Ayuntamiento de Marbella").first
    enlace.wait_for(state="visible", timeout=60000)
    enlace.click()

    # La ficha del perfil tiene que cargar antes de buscar sus pestanas.
    pg.wait_for_selector("text=Órgano de Contratación", timeout=60000)

    tab = pg.get_by_text("Documentos", exact=True).first
    tab.wait_for(state="visible", timeout=60000)
    tab.click()

    # La pestana se rellena por AJAX y por partes. Esperar a que aparezca la
    # primera fila no basta: la primera vez que se hizo asi se leyeron 24 de
    # los 48 documentos. Se espera a que el recuento deje de crecer.
    pg.wait_for_selector("div[id^='epigrafe_'] div.flex-inline-xxs", timeout=60000)
    SEL = "div[id^='epigrafe_'] div.flex-inline-xxs"
    previo, estable = -1, 0
    for _ in range(40):
        n = pg.eval_on_selector_all(SEL, "els => els.length")
        estable = estable + 1 if n == previo else 0
        previo = n
        if estable >= 3:
            break
        pg.wait_for_timeout(500)
    else:
        print(f"  aviso: el listado seguia creciendo ({previo} filas) al agotar la espera")
    return pg.evaluate(JS_FILAS)


def main():
    with sync_playwright() as p:
        nav = p.chromium.launch(**({} if os.environ.get("CI") else {"channel": "chrome"}))
        # El portal sirve paginas distintas segun el navegador y el idioma, y
        # desde un runner el chromium pelado no trae ni UA de escritorio ni
        # locale espanol.
        ctx = nav.new_context(
            accept_downloads=True,
            locale="es-ES",
            timezone_id="Europe/Madrid",
            viewport={"width": 1500, "height": 1200},
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"),
        )
        pg = ctx.new_page()

        filas = []
        for intento in (1, 2, 3):
            try:
                filas = abrir_documentos(pg)
                if filas:
                    break
                print(f"  intento {intento}: la pestana Documentos vino vacia")
            except Exception as e:
                print(f"  intento {intento}: {type(e).__name__}: {str(e)[:120]}")
            if intento < 3:
                pg.wait_for_timeout(5000)

        if not filas:
            # Dejar rastro para poder ver que encontro el runner.
            try:
                pg.screenshot(path=str(DEST / "_fallo.png"), full_page=True)
                (DEST / "_fallo.html").write_text(pg.content(), encoding="utf-8")
            except Exception:
                pass
            nav.close()
            sys.exit("El perfil no devolvio ningun documento tras 3 intentos.")
        print(f"{len(filas)} documentos publicados en el perfil")

        inventario = []
        for f in filas:
            c = clase(f["titulo"])
            if not c:
                continue
            a, t = anio(f["titulo"]), trimestre(f["titulo"])
            nombre = f"{c}_{a}" + (f"_T{t}" if t else "_anual")
            if "COMPLEMENTARI" in f["titulo"].upper():
                nombre += "_complementario"
            destino = DEST / f"{nombre}__{slug(f['titulo'])}.pdf"

            if destino.exists() and destino.stat().st_size > 0:
                print(f"  SKIP  {destino.name} (ya descargado)")
            else:
                r = ctx.request.get(f["url"], timeout=180000)
                if r.status != 200:
                    print(f"  ERROR {f['titulo'][:50]} -> HTTP {r.status}")
                    continue
                destino.write_bytes(r.body())
                print(f"  OK    {destino.name}  ({destino.stat().st_size/1e3:.0f} KB)")

            inventario.append({
                "clase": c, "anio": a, "trimestre": t,
                "complementario": "COMPLEMENTARI" in f["titulo"].upper(),
                "titulo": f["titulo"], "publicado": f["fecha"],
                "url": f["url"], "fichero": destino.name,
            })
        nav.close()

    # Red de seguridad: el perfil solo crece. Si una lectura trae menos
    # documentos que la anterior es que la pagina no habia terminado de
    # cargar, y sobrescribir el inventario tiraria datos buenos.
    previo = DEST / "inventario.json"
    if previo.exists():
        antes = len(json.loads(previo.read_text(encoding="utf-8")))
        if len(inventario) < antes:
            sys.exit(f"ABORTA: se han leido {len(inventario)} documentos y el "
                     f"inventario anterior tenia {antes}. No se sobrescribe.")

    (DEST / "inventario.json").write_text(
        json.dumps(inventario, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\ninventario -> {DEST / 'inventario.json'}  ({len(inventario)} documentos de datos)")
    for c in ("mayores", "menores", "modificados"):
        aa = sorted({d["anio"] for d in inventario if d["clase"] == c and d["anio"]})
        print(f"  {c:12s}: {aa}")


if __name__ == "__main__":
    main()
