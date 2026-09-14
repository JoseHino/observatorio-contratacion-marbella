"""Contratos menores del Ayuntamiento de Marbella.

El Ayuntamiento NO publica sus contratos menores en la PLACSP (comprobado
fichero a fichero en los datos abiertos 2018-2026: las apariciones de
"Marbella" corresponden a contratos de otros organismos ejecutados aqui).
La fuente son los listados anuales que el propio Ayuntamiento publica.

Produce dos cosas distintas y no las mezcla:

  * `oficial`  -> los totales certificados por el Ayuntamiento (numero de
                  contratos e importe por ano, tipo y trimestre). Es lo que
                  alimenta las graficas agregadas.
  * `registros`-> el detalle contrato a contrato, para el buscador. Tiene mas
                  filas que el total oficial porque los listados vienen de
                  volcados en PDF con lineas repetidas; se deduplican las
                  repeticiones exactas y se avisa de la diferencia.
"""
import json
import pathlib
import re
import sys
import unicodedata
from collections import defaultdict

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT.parent / "Contratación" / "MENORES"
OUT = ROOT / "menores_marbella.json"

# Hoja de detalle preferida para cada ejercicio (la mas completa disponible).
DETALLE = [
    ("CONTRATOS MENORES.xlsx", "2020", 2020),
    ("CONTRATOS MENORES.xlsx", "2021", 2021),
    ("CONTRATOS MENORES.xlsx", "2022", 2022),
    ("CONTRATOS MENORES.xlsx", "2023", 2023),
    ("CONTRATOS MENORES 2024.xlsx", "page 1", 2024),
    ("2025 Contratos menores.xlsx", "2025-T1", 2025),
    ("2025 Contratos menores.xlsx", "2025-T2", 2025),
    ("2025 Contratos menores.xlsx", "2025-T3", 2025),
    ("2025 Contratos menores.xlsx", "2025-T4", 2025),
]

TOTALES = ("2025 Contratos menores.xlsx", "TOTALES")


def norm(s):
    # El indicador ordinal se quita ANTES de NFKD: si no, "Nº" se descompone
    # en "No" y "Nº CONTRATOS" deja de parecerse a "n contratos".
    s = str(s or "").replace("º", "").replace("°", "").replace("ª", "")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def num(v):
    """Importe robusto: acepta 1.234,56 y 1234.56."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 2)
    s = str(v).strip().replace("€", "").replace(" ", "")
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


# --------------------------------------------------------------- totales ---
def leer_totales():
    """La hoja TOTALES apila un bloque por ejercicio: cabecera con el ano,
    una tabla de numero de contratos y otra de importes, ambas por trimestre."""
    d = pd.read_excel(SRC / TOTALES[0], sheet_name=TOTALES[1], header=None)
    oficial, anio, seccion = {}, None, None
    for _, row in d.iterrows():
        celdas = [c for c in row.tolist() if not (isinstance(c, float) and pd.isna(c))]
        if not celdas:
            continue
        c0 = norm(celdas[0])
        if c0 == "contratos menores" and len(celdas) > 1 and num(celdas[1]):
            anio = int(num(celdas[1]))
            oficial.setdefault(anio, {"n": {}, "importe": {}})
            seccion = None
            continue
        if c0 == "n contratos":
            seccion = "n"
            continue
        if c0 == "importe contratos":
            seccion = "importe"
            continue
        if anio and seccion and c0 in ("obras", "servicios", "suministros", "totales"):
            clave = {"obras": "Obras", "servicios": "Servicios",
                     "suministros": "Suministros", "totales": "TOTAL"}[c0]
            trims = [num(c) for c in celdas[1:6]]
            oficial[anio][seccion][clave] = {
                "trimestres": trims[:4],
                "total": trims[4] if len(trims) > 4 and trims[4] is not None else None,
            }
    return oficial


# --------------------------------------------------------------- detalle ---
ALIAS = {
    "ejercicio": "ejercicio",
    "n expediente clave": "expediente", "n expediente / clave": "expediente",
    "n expediente": "expediente",
    "n de contrato": "n_contrato", "n contrato": "n_contrato",
    "descripcion del contrato": "objeto",
    "tipo de contrato": "tipo", "tipo": "tipo",
    "n.i.f. adjudicatario": "nif_adj", "n.i.f. adjudicatari o": "nif_adj",
    "n.i.f. adjudicatario": "nif_adj",
    "adjudicatario (nombre o razon social)": "adjudicatario", "adjudicatario": "adjudicatario",
    "duracion": "duracion", "duracion (meses)": "duracion_meses",
    "importe adjudicacion (iva incluido)": "importe",
    "importe adjudicacion (iva incl.)": "importe",
    "importe adjudicacion (iva in cluido)": "importe",
    "importe adjudicaci on (iva incluido)": "importe",
    "n.i.f. entidad remitente": "nif_entidad",
    "entidad remitente (nombre o razon social)": "entidad",
    "trim.": "trimestre", "observaciones": "observaciones",
}


def mapea(cabecera):
    """Empareja cada columna con su campo; tolera los saltos de linea y las
    separaciones que introduce el volcado desde PDF."""
    cols = {}
    for i, c in enumerate(cabecera):
        k = norm(c)
        if not k:
            continue
        if k in ALIAS:
            cols[ALIAS[k]] = i
            continue
        if "importe" in k and "adjudicaci" in k:
            cols["importe"] = i
        elif "n.i.f" in k and "adjudicatari" in k:
            cols["nif_adj"] = i
        elif "n.i.f" in k and "remitente" in k:
            cols["nif_entidad"] = i
        elif k.startswith("adjudicatario"):
            cols["adjudicatario"] = i
        elif "descripcion" in k:
            cols["objeto"] = i
        elif "expediente" in k:
            cols.setdefault("expediente", i)
        elif "contrato" in k and "tipo" not in k and "importe" not in k:
            cols.setdefault("n_contrato", i)
        elif k.startswith("tipo"):
            cols["tipo"] = i
        elif k.startswith("duracion"):
            cols.setdefault("duracion", i)
        elif k.startswith("ejercicio"):
            cols["ejercicio"] = i
    return cols


TIPO_CANON = {"obra": "Obras", "obras": "Obras",
              "servicio": "Servicios", "servicios": "Servicios",
              "suministro": "Suministros", "suministros": "Suministros"}


def leer_detalle(fichero, hoja, anio):
    d = pd.read_excel(SRC / fichero, sheet_name=hoja, header=None)
    # La cabecera es la primera fila que contiene "Ejercicio".
    cab_i = None
    for i in range(min(8, len(d))):
        if any(norm(c) == "ejercicio" for c in d.iloc[i].tolist()):
            cab_i = i
            break
    if cab_i is None:
        print(f"   AVISO: sin cabecera en {fichero}/{hoja}")
        return []
    cols = mapea(d.iloc[cab_i].tolist())
    if "importe" not in cols or "objeto" not in cols:
        print(f"   AVISO: faltan columnas clave en {fichero}/{hoja}: {sorted(cols)}")
        return []

    filas = []
    for _, row in d.iloc[cab_i + 1:].iterrows():
        v = row.tolist()

        def g(campo):
            i = cols.get(campo)
            if i is None or i >= len(v):
                return ""
            x = v[i]
            if isinstance(x, float) and pd.isna(x):
                return ""
            return re.sub(r"\s+", " ", str(x)).strip()

        importe = num(v[cols["importe"]]) if cols["importe"] < len(v) else None
        objeto = g("objeto")
        if importe is None or not objeto:
            continue
        ej = num(g("ejercicio"))
        filas.append({
            "anio": int(ej) if ej and 2000 <= ej <= 2035 else anio,
            "expediente": g("expediente") or g("n_contrato"),
            "n_contrato": g("n_contrato"),
            "objeto": objeto,
            "tipo": TIPO_CANON.get(norm(g("tipo")), g("tipo") or "Sin especificar"),
            "adjudicatario": g("adjudicatario"),
            "nif_adjudicatario": g("nif_adj").replace("-", "").upper(),
            "duracion": g("duracion"),
            "importe_con_iva": importe,
            "trimestre": hoja[-2:] if hoja.startswith("2025-") else g("trimestre"),
        })
    return filas


# ------------------------------------------------------------------ main ---
print("== totales oficiales publicados por el Ayuntamiento ==")
oficial = leer_totales()
for a in sorted(oficial):
    t = oficial[a]
    print(f"  {a}: {t['n'].get('TOTAL', {}).get('total')} contratos · "
          f"{t['importe'].get('TOTAL', {}).get('total'):,.2f} € (IVA incl.)")

print("\n== detalle contrato a contrato ==")
registros, vistos = [], set()
dup = 0
for fichero, hoja, anio in DETALLE:
    filas = leer_detalle(fichero, hoja, anio)
    n_dup = 0
    for r in filas:
        clave = (r["anio"], r["expediente"], r["n_contrato"], r["objeto"][:120],
                 r["nif_adjudicatario"], r["importe_con_iva"])
        if clave in vistos:
            n_dup += 1
            continue
        vistos.add(clave)
        registros.append(r)
    dup += n_dup
    print(f"  {fichero:32s} {hoja:9s} -> {len(filas):4d} filas, {n_dup:3d} repetidas")

por_anio = defaultdict(lambda: [0, 0.0])
for r in registros:
    por_anio[r["anio"]][0] += 1
    por_anio[r["anio"]][1] += r["importe_con_iva"] or 0

print(f"\n{len(registros)} contratos menores unicos ({dup} filas repetidas descartadas)\n")
print(f"{'anio':>6} {'detalle':>9} {'oficial':>9}  {'importe detalle':>18} {'importe oficial':>18}")
for a in sorted(por_anio):
    of = oficial.get(a, {})
    n_of = of.get("n", {}).get("TOTAL", {}).get("total")
    i_of = of.get("importe", {}).get("TOTAL", {}).get("total")
    print(f"{a:>6} {por_anio[a][0]:>9} {str(n_of or '—'):>9}  "
          f"{por_anio[a][1]:>18,.2f} {(f'{i_of:,.2f}' if i_of else '—'):>18}")

OUT.write_text(json.dumps({
    "fuente": "Relación anual de contratos menores publicada por el Ayuntamiento de Marbella",
    "oficial": oficial,
    "registros": registros,
}, ensure_ascii=False), encoding="utf-8")
print("\n->", OUT, f"{OUT.stat().st_size/1e6:.2f} MB")
