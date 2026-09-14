"""Verificacion del observatorio: que TODAS las graficas pinten lienzo.

Regla del kit: que la pagina cargue no significa que haya datos. Se cuenta
`.obs-plot` frente a los que tienen <canvas>, en claro y en oscuro, y se
recogen los avisos de consola (doble eje, novena serie...).
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = (ROOT / "observatorio" / "index.html").as_uri()
SHOTS = ROOT / "_capturas"

# En local se usa el Chrome instalado (las versiones de los navegadores de
# Playwright no casan); en un runner solo esta el chromium que trae Playwright.
import os
LANZAR = {} if os.environ.get("CI") else {"channel": "chrome"}
SHOTS.mkdir(exist_ok=True)

# Las secciones ya pintadas siguen en el DOM (solo se ocultan), asi que el
# diagnostico se acota a la seccion activa o contaria las graficas de todas.
DIAG = """id => {
  const sec = document.getElementById('sec-' + id);
  const plots = [...sec.querySelectorAll('.obs-plot')];
  return {
    plots: plots.length,
    conCanvas: plots.filter(p => p.querySelector('canvas')).length,
    vacios: plots.filter(p => p.querySelector('.obs-msg')).length,
    kpisVacios: [...sec.querySelectorAll('.obs-kpi .v')]
       .filter(v => v.textContent.trim().startsWith('\\u2014')).length
  };
}"""

SECS = ["panorama", "mayores", "menores", "modificados", "adjudicatarios", "competencia", "buscador", "documentos"]
fallos = []

with sync_playwright() as p:
    nav = p.chromium.launch(**LANZAR)
    for tema in ("light", "dark"):
        ctx = nav.new_context(viewport={"width": 1440, "height": 1000}, color_scheme=tema)
        pg = ctx.new_page()
        msgs = []
        pg.on("console", lambda m: msgs.append(f"{m.type}: {m.text}"))
        pg.on("pageerror", lambda e: msgs.append(f"pageerror: {e}"))
        pg.goto(URL)
        pg.wait_for_timeout(1500)
        pg.evaluate("t => document.documentElement.setAttribute('data-theme', t)", tema)

        for sec in SECS:
            pg.evaluate("id => Obs.ir(id)", sec)
            pg.wait_for_timeout(1400)
            d = pg.evaluate(DIAG, sec)
            ok = d["conCanvas"] == d["plots"] and d["vacios"] == 0
            print(f"[{tema}] {sec:12s} plots={d['plots']:2d} canvas={d['conCanvas']:2d} "
                  f"vacios={d['vacios']} kpis_sin_dato={d['kpisVacios']}  {'OK' if ok else 'FALLA'}")
            if not ok:
                fallos.append(f"{tema}/{sec}: {d}")
            pg.screenshot(path=str(SHOTS / f"{tema}-{sec}.png"), full_page=True)

        # el buscador: comprobar que filtra de verdad
        if tema == "light":
            pg.evaluate("id => Obs.ir(id)", "buscador")
            pg.wait_for_timeout(600)
            antes = pg.inner_text("#bs-resumen")
            pg.fill("#bs-q", "jardines")
            pg.wait_for_timeout(700)
            despues = pg.inner_text("#bs-resumen")
            filas = pg.eval_on_selector_all(".bs-row", "n => n.length")
            print(f"\nbuscador: sin filtro -> {antes.strip()}")
            print(f"buscador: 'jardines' -> {despues.strip()}  ({filas} filas en pantalla)")
            if antes == despues:
                fallos.append("el buscador no filtra")
            if filas:
                pg.click(".bs-row")
                pg.wait_for_timeout(300)
                abierto = pg.eval_on_selector_all(".bs-det:not([hidden])", "n => n.length")
                print(f"buscador: detalle desplegado -> {abierto}")
                if not abierto:
                    fallos.append("el detalle de la fila no se despliega")
            pg.screenshot(path=str(SHOTS / "light-buscador-filtrado.png"), full_page=True)

        raros = [m for m in msgs if m.startswith(("error", "warning", "pageerror"))]
        if raros:
            print(f"\n[{tema}] consola:")
            for m in raros[:15]:
                print("   ", m[:180])
        ctx.close()
    nav.close()

print("\n" + ("TODO OK" if not fallos else "FALLOS:\n  " + "\n  ".join(fallos)))
print("capturas en", SHOTS)
sys.exit(1 if fallos else 0)
