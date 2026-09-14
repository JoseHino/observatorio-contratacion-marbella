"""Empaqueta el observatorio en un unico .html autocontenido.

Incrusta obs.css, obs-charts.js, obs-ui.js, data.js y app.js, y ademas la
libreria ECharts (descargada y cacheada), de modo que el fichero funciona con
doble clic y sin conexion. La version en carpeta (observatorio/) sigue siendo
la que se mantiene; esta es la copia para enviar.
"""
import pathlib
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
OBS = ROOT / "observatorio"
DEST = ROOT / "Observatorio Transparencia Marbella.html"
ECHARTS_URL = "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"
CACHE = ROOT / "_raw" / "echarts.min.js"

if not CACHE.exists():
    print("descargando ECharts…")
    req = urllib.request.Request(ECHARTS_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        CACHE.write_bytes(r.read())

html = (OBS / "index.html").read_text(encoding="utf-8")


def leer(rel):
    return (OBS / rel).read_text(encoding="utf-8")


# CSS del kit -> <style> en linea
html = html.replace(
    '<link rel="stylesheet" href="assets/obs.css">',
    "<style>\n" + leer("assets/obs.css") + "\n</style>",
)

# Scripts -> <script> en linea. Las cierres de etiqueta dentro del JS se
# escapan para que el navegador no corte el bloque antes de tiempo.
def inline(src, contenido):
    return "<script>\n" + contenido.replace("</script", "<\\/script") + "\n</script>"


html = html.replace(
    '<script src="' + ECHARTS_URL + '"></script>',
    inline(ECHARTS_URL, CACHE.read_text(encoding="utf-8")),
)
for rel in ("assets/obs-charts.js", "assets/obs-ui.js", "data/data.js", "app.js"):
    html = re.sub(
        r'<script src="' + re.escape(rel) + r'"></script>',
        lambda m, rel=rel: inline(rel, leer(rel)),
        html,
    )

sobran = re.findall(r'<script src="[^"]+"></script>|<link rel="stylesheet"[^>]*>', html)
if sobran:
    print("AVISO: quedan referencias externas sin incrustar:", sobran)

DEST.write_text(html, encoding="utf-8")
print(f"{DEST.name}  {DEST.stat().st_size/1e6:.2f} MB")
