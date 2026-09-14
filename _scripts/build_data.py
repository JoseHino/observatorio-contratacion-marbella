"""Agrega las dos fuentes del observatorio y escribe observatorio/data/data.js.

  * Contratos MAYORES -> datos abiertos de la PLACSP (fuente="mayores").
  * Contratos MENORES -> dos sitios a la vez, y no dicen lo mismo:
      - la PLACSP, desde 2022 (fuente="menores"), expediente a expediente y con
        ficha enlazable;
      - los listados anuales del Ayuntamiento (menores_marbella.json), que son
        los TOTALES CERTIFICADOS y llegan mas atras (2020-2021), pero sin ficha.
    Las graficas agregadas usan el total certificado, que es la cifra que el
    Ayuntamiento firma; el buscador usa el detalle de la PLACSP donde lo hay y
    el listado municipal en los anos en que la PLACSP no trae nada. La
    diferencia entre ambos se publica como indicador de cobertura.

Toda la serie monetaria se expresa en EUROS CON IVA, que es la unica base
comun a las dos fuentes: los listados de menores solo publican el importe con
IVA. Donde se usa el importe sin IVA se dice expresamente.
"""
import json
import pathlib
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "observatorio" / "data" / "data.js"
OUT.parent.mkdir(parents=True, exist_ok=True)

ANIO_MIN = 2018          # la LCSP 9/2017 obliga a publicar en perfil desde 03/2018
ANIO_MAX = datetime.now().year
ANIOS = list(range(ANIO_MIN, ANIO_MAX + 1))
ANIO_MIN_MENORES = 2020  # primer listado de menores disponible

MAYORES = json.loads((ROOT / "contratos_marbella.json").read_text(encoding="utf-8"))
MEN = json.loads((ROOT / "menores_marbella.json").read_text(encoding="utf-8"))
OFICIAL = {int(a): v for a, v in MEN["oficial"].items()}
MENORES = [r for r in MEN["registros"] if ANIO_MIN <= r["anio"] <= ANIO_MAX]

_EN_RANGO = [r for r in MAYORES if r.get("anio") and ANIO_MIN <= r["anio"] <= ANIO_MAX]

# El fichero de la PLACSP trae las dos clases: separarlas o los menores se
# cuentan como mayores y el panel miente por partida doble.
D = [r for r in _EN_RANGO if r.get("fuente") == "mayores"]
PLACSP_MEN = [r for r in _EN_RANGO if r.get("fuente") == "menores"]
ANIOS_PLACSP_MEN = sorted({r["anio"] for r in PLACSP_MEN})


# --------------------------------------------------------------- importes ---
def adj_con_iva(r):
    """Importe adjudicado CON IVA; si el expediente no esta adjudicado todavia,
    el presupuesto base de licitacion, que es la mejor estimacion publicada."""
    v = [a["importe_con_iva"] for a in r["adjudicaciones"] if a.get("importe_con_iva")]
    if v:
        return round(sum(v), 2)
    return r.get("presupuesto_con_iva") or 0


def adj_sin_iva(r):
    return r.get("importe_adjudicacion") or r.get("presupuesto_sin_iva") or 0


def serie(f, datos=None):
    por = defaultdict(list)
    for r in (D if datos is None else datos):
        por[r["anio"]].append(r)
    return [f(por.get(a, [])) for a in ANIOS]


def ofic(anio, seccion, clave):
    return (OFICIAL.get(anio, {}).get(seccion, {}).get(clave) or {}).get("total")


def placsp_men_n(anio):
    return sum(1 for r in PLACSP_MEN if r["anio"] == anio) or None


def placsp_men_imp(anio):
    s = sum(adj_con_iva(r) for r in PLACSP_MEN if r["anio"] == anio)
    return round(s, 2) or None


def menores_n(anio):
    """Numero de contratos menores del ano. Manda el total certificado por el
    Ayuntamiento; si ese ano no esta certificado todavia, lo publicado en la
    PLACSP; y en ultimo termino el recuento del listado municipal de detalle."""
    v = ofic(anio, "n", "TOTAL")
    if v is not None:
        return int(v)
    return placsp_men_n(anio) or (sum(1 for r in MENORES if r["anio"] == anio) or None)


def menores_imp(anio):
    v = ofic(anio, "importe", "TOTAL")
    if v is not None:
        return round(v, 2)
    v = placsp_men_imp(anio)
    if v is not None:
        return v
    s = sum(r["importe_con_iva"] or 0 for r in MENORES if r["anio"] == anio)
    return round(s, 2) or None


# --------------------------------------------------------------- resumen ---
resumen = {
    "x": ANIOS,
    "n_mayores": serie(len),
    "n_menores": [menores_n(a) for a in ANIOS],
    "imp_mayores": serie(lambda rs: round(sum(adj_con_iva(r) for r in rs), 2)),
    "imp_menores": [menores_imp(a) for a in ANIOS],
    "presupuesto": serie(lambda rs: round(sum(r.get("presupuesto_con_iva") or 0 for r in rs), 2)),
    "adjudicado": serie(lambda rs: round(sum(adj_con_iva(r) for r in rs), 2)),
    # peso del contrato menor sobre el conjunto de la contratacion municipal
    "pct_menores_num": [],
    "pct_menores_imp": [],
}
for i, a in enumerate(ANIOS):
    nm, nM = resumen["n_menores"][i], resumen["n_mayores"][i]
    im, iM = resumen["imp_menores"][i], resumen["imp_mayores"][i]
    resumen["pct_menores_num"].append(round(nm / (nm + nM) * 100, 1) if nm and (nm + nM) else None)
    resumen["pct_menores_imp"].append(round(im / (im + iM) * 100, 1) if im and (im + iM) else None)

# ------------------------------------------------------- mayores: tipos ----
TIPOS = [t for t, _ in Counter(r["tipo"] for r in D if r["tipo"]).most_common(6)]
tipos = {
    "x": ANIOS, "nombres": TIPOS,
    "n": [serie(lambda rs, t=t: sum(1 for r in rs if r["tipo"] == t)) for t in TIPOS],
    "importe": [serie(lambda rs, t=t: round(sum(adj_con_iva(r) for r in rs if r["tipo"] == t), 2)) for t in TIPOS],
}

# ---------------------------------------------- mayores: procedimientos ----
cp_n, cp_i = Counter(), defaultdict(float)
for r in D:
    p = r["procedimiento"] or "Sin especificar"
    cp_n[p] += 1
    cp_i[p] += adj_con_iva(r)
PROCS = [p for p, _ in cp_n.most_common(8)]
procedimientos = {
    "x": PROCS,
    "n": [cp_n[p] for p in PROCS],
    "importe": [round(cp_i[p], 2) for p in PROCS],
    "por_anio": {
        "x": ANIOS, "nombres": PROCS[:6],
        "n": [serie(lambda rs, p=p: sum(1 for r in rs if (r["procedimiento"] or "Sin especificar") == p))
              for p in PROCS[:6]],
    },
}

es_n = Counter(r["estado"] or "Sin estado" for r in D)
estados = {"x": [e for e, _ in es_n.most_common()], "n": [n for _, n in es_n.most_common()]}

# ------------------------------------------------------------- menores -----
MEN_TIPOS = ["Servicios", "Suministros", "Obras"]
# Solo los ejercicios con listado publicado: una columna vacia al final no
# informa de nada y descuadra la lectura de la serie.
ANIOS_MEN = [a for a in ANIOS
             if a >= ANIO_MIN_MENORES and (a in OFICIAL or any(r["anio"] == a for r in MENORES))]


def men_tipo(anio, tipo, seccion):
    v = ofic(anio, seccion, tipo)
    if v is not None:
        return round(v, 2) if seccion == "importe" else int(v)
    filas = [r for r in MENORES if r["anio"] == anio and r["tipo"] == tipo]
    if not filas:
        return None
    return round(sum(r["importe_con_iva"] or 0 for r in filas), 2) if seccion == "importe" else len(filas)


# Reparto trimestral: solo existe en los totales certificados.
def men_trim(anio, seccion):
    t = (OFICIAL.get(anio, {}).get(seccion, {}).get("TOTAL") or {}).get("trimestres")
    return t if t else [None] * 4


menores = {
    "x": ANIOS_MEN,
    "nombres": MEN_TIPOS,
    "n": [[men_tipo(a, t, "n") for a in ANIOS_MEN] for t in MEN_TIPOS],
    "importe": [[men_tipo(a, t, "importe") for a in ANIOS_MEN] for t in MEN_TIPOS],
    "trimestres": {
        "x": ["T1", "T2", "T3", "T4"],
        "anios": [a for a in ANIOS_MEN if OFICIAL.get(a)],
        "importe": [men_trim(a, "importe") for a in ANIOS_MEN if OFICIAL.get(a)],
        "n": [men_trim(a, "n") for a in ANIOS_MEN if OFICIAL.get(a)],
    },
    "importe_medio": [
        round(menores_imp(a) / menores_n(a), 2) if menores_n(a) and menores_imp(a) else None
        for a in ANIOS_MEN
    ],
    "n_detalle": len(MENORES),
    "anios_certificados": sorted(OFICIAL),
}

# -------------------------------------------------------- adjudicatarios ---
emp_i, emp_n = defaultdict(float), Counter()
emp_men_i, emp_men_n = defaultdict(float), Counter()
for r in D:
    for a in r["adjudicaciones"]:
        nom = (a.get("adjudicatario") or "").strip()
        if nom:
            emp_i[nom] += a.get("importe_con_iva") or 0
            emp_n[nom] += 1
for r in MENORES:
    nom = (r.get("adjudicatario") or "").strip()
    if nom:
        emp_men_i[nom] += r["importe_con_iva"] or 0
        emp_men_n[nom] += 1

todos_i = defaultdict(float)
todos_n = Counter()
for d_, n_ in ((emp_i, emp_n), (emp_men_i, emp_men_n)):
    for k, v in d_.items():
        todos_i[k] += v
    todos_n.update(n_)

top_imp = sorted(todos_i.items(), key=lambda kv: -kv[1])[:15]
top_num = todos_n.most_common(15)
total_emp = sum(todos_i.values()) or 1
empresas = {
    "top_importe": {"x": [n for n, _ in top_imp][::-1], "v": [round(v, 2) for _, v in top_imp][::-1]},
    "top_numero": {"x": [n for n, _ in top_num][::-1], "v": [v for _, v in top_num][::-1]},
    "top_menores": {
        "x": [n for n, _ in sorted(emp_men_i.items(), key=lambda kv: -kv[1])[:15]][::-1],
        "v": [round(v, 2) for _, v in sorted(emp_men_i.items(), key=lambda kv: -kv[1])[:15]][::-1],
    },
    "n_distintas": len(todos_i),
    "n_solo_mayores": len(emp_i),
    "n_solo_menores": len(emp_men_i),
    "concentracion": round(sum(v for _, v in top_imp[:10]) / total_emp * 100, 1),
    "n_con_adjudicatario": sum(1 for r in D if any(a.get("adjudicatario") for a in r["adjudicaciones"])),
}

# ------------------------------------------------------------------ CPV ----
CPV_DIV = {
    "03": "Agricultura y pesca", "09": "Energía y combustibles", "14": "Minería y minerales",
    "15": "Alimentación y bebidas", "16": "Maquinaria agrícola", "18": "Vestuario y calzado",
    "19": "Cuero y textiles", "22": "Impresos y publicaciones", "24": "Productos químicos",
    "30": "Equipos informáticos y de oficina", "31": "Material eléctrico", "32": "Radio, TV y telecomunicaciones",
    "33": "Equipos médicos y farmacia", "34": "Vehículos y transporte", "35": "Seguridad y defensa",
    "37": "Instrumentos musicales, deporte y juegos", "38": "Equipos de laboratorio y precisión",
    "39": "Mobiliario y limpieza", "41": "Agua", "42": "Maquinaria industrial",
    "43": "Maquinaria de obra y minería", "44": "Materiales de construcción", "45": "Obras de construcción",
    "48": "Software", "50": "Reparación y mantenimiento", "51": "Instalación de equipos",
    "55": "Hostelería y restauración", "60": "Transporte", "63": "Servicios auxiliares de transporte",
    "64": "Correos y telecomunicaciones", "65": "Suministros públicos", "66": "Servicios financieros y seguros",
    "70": "Servicios inmobiliarios", "71": "Arquitectura, ingeniería y urbanismo",
    "72": "Servicios TI y consultoría", "73": "I+D", "75": "Administración pública y defensa",
    "76": "Servicios petrolíferos y gasísticos", "77": "Agricultura, silvicultura y jardinería",
    "79": "Servicios de empresa y jurídicos", "80": "Educación y formación", "85": "Salud y servicios sociales",
    "90": "Saneamiento y medio ambiente", "92": "Cultura, ocio y deporte", "98": "Otros servicios",
}
cpv_i, cpv_n = defaultdict(float), Counter()
for r in D:
    nom = CPV_DIV.get((r["cpv"][0][:2] if r["cpv"] else ""), "Otras materias")
    cpv_i[nom] += adj_con_iva(r)
    cpv_n[nom] += 1
top_cpv = sorted(cpv_i.items(), key=lambda kv: -kv[1])[:12]
cpv = {
    "x": [n for n, _ in top_cpv][::-1],
    "importe": [round(v, 2) for _, v in top_cpv][::-1],
    "n": [cpv_n[n] for n, _ in top_cpv][::-1],
}


# ------------------------------------------------------------ competencia --
def ofertas_de(r):
    v = [a["n_ofertas"] for a in r["adjudicaciones"] if a.get("n_ofertas")]
    return sum(v) if v else None


def media_ofertas(rs):
    v = [ofertas_de(r) for r in rs if ofertas_de(r)]
    return round(sum(v) / len(v), 2) if v else None


def pct_una_oferta(rs):
    v = [ofertas_de(r) for r in rs if ofertas_de(r)]
    return round(sum(1 for x in v if x == 1) / len(v) * 100, 1) if v else None


def baja_media(rs):
    """Baja de adjudicacion, agregando importes (no promediando porcentajes),
    en euros SIN IVA que es donde ambas magnitudes son comparables."""
    par = [(r["presupuesto_sin_iva"], r["importe_adjudicacion"]) for r in rs
           if r.get("presupuesto_sin_iva") and r.get("importe_adjudicacion")
           and 0 < r["importe_adjudicacion"] <= r["presupuesto_sin_iva"] * 1.5]
    if not par:
        return None
    pres, adj = sum(p for p, _ in par), sum(a for _, a in par)
    return round((pres - adj) / pres * 100, 1) if pres else None


def n_informados(rs):
    return sum(1 for r in rs if ofertas_de(r)) or None


competencia = {
    "x": ANIOS,
    "media_ofertas": serie(media_ofertas),
    "pct_una_oferta": serie(pct_una_oferta),
    "baja_media": serie(baja_media),
    "n_informados": serie(n_informados),
}

# ------------------------------------------------------- indice de busqueda -
CAMPOS = ["a", "f", "ex", "ob", "ti", "pr", "es", "adj", "nif", "imp", "pre", "fa", "or", "cp", "url"]


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


filas = []
for r in D:
    adjs = sorted({a["adjudicatario"] for a in r["adjudicaciones"] if a.get("adjudicatario")})
    nifs = sorted({a["nif_adjudicatario"] for a in r["adjudicaciones"] if a.get("nif_adjudicatario")})
    filas.append([
        r["anio"], "m", r["expediente"] or "", (r["objeto"] or "")[:400],
        r["tipo"] or "", r["procedimiento"] or "", r["estado"] or "",
        "; ".join(adjs), "; ".join(nifs),
        round(adj_con_iva(r), 2) or None, r.get("presupuesto_con_iva"),
        r.get("fecha_adjudicacion") or "", r["organo"] or "",
        (r["cpv_desc"][0] if r.get("cpv_desc") else ""), r.get("enlace") or "",
    ])
# Los menores se cogen de la PLACSP en los anos en que esta los publica (traen
# ficha) y del listado municipal en los anos en que no (2020-2021). Nunca de
# los dos a la vez: serian el mismo contrato dos veces.
for r in PLACSP_MEN:
    adjs = sorted({a["adjudicatario"] for a in r["adjudicaciones"] if a.get("adjudicatario")})
    nifs = sorted({a["nif_adjudicatario"] for a in r["adjudicaciones"] if a.get("nif_adjudicatario")})
    filas.append([
        r["anio"], "M", r["expediente"] or "", (r["objeto"] or "")[:400],
        r["tipo"] or "", "Contrato menor", r["estado"] or "Adjudicado",
        "; ".join(adjs), "; ".join(nifs),
        round(adj_con_iva(r), 2) or None, r.get("presupuesto_con_iva"),
        r.get("fecha_adjudicacion") or "", r["organo"] or "",
        (r["cpv_desc"][0] if r.get("cpv_desc") else ""), r.get("enlace") or "",
    ])
for r in MENORES:
    if r["anio"] in ANIOS_PLACSP_MEN:
        continue
    ref = " · ".join(x for x in (r.get("expediente"), r.get("n_contrato")) if x)
    filas.append([
        r["anio"], "M", ref, (r["objeto"] or "")[:400],
        r["tipo"] or "", "Contrato menor", "Adjudicado",
        r.get("adjudicatario") or "", r.get("nif_adjudicatario") or "",
        r.get("importe_con_iva"), None,
        "", "Ayuntamiento de Marbella", "", "",
    ])

filas.sort(key=lambda f: (-(f[0] or 0), f[2] or ""))
claves = [norm(" ".join(str(f[i] or "") for i in (2, 3, 7, 8, 12, 13))) for f in filas]

# ------------------------------------------------- cobertura de la PLACSP ---
# Cuanto de lo que el Ayuntamiento certifica en contratos menores llega a la
# Plataforma. Solo tiene sentido en los anos con las dos cifras.
cobertura = {
    "x": ANIOS,
    "certificado_n": [ofic(a, "n", "TOTAL") for a in ANIOS],
    "certificado_imp": [ofic(a, "importe", "TOTAL") for a in ANIOS],
    "placsp_n": [placsp_men_n(a) for a in ANIOS],
    "placsp_imp": [placsp_men_imp(a) for a in ANIOS],
    "pct_n": [],
    "pct_imp": [],
}
for i, a in enumerate(ANIOS):
    cn, pn = cobertura["certificado_n"][i], cobertura["placsp_n"][i]
    ci, pi = cobertura["certificado_imp"][i], cobertura["placsp_imp"][i]
    cobertura["pct_n"].append(round(pn / cn * 100, 1) if cn and pn else None)
    cobertura["pct_imp"].append(round(pi / ci * 100, 1) if ci and pi else None)

# ------------------------------------------------------------------ meta ---
imp_may = round(sum(adj_con_iva(r) for r in D), 2)
imp_men = round(sum(v for v in resumen["imp_menores"] if v), 2)
meta = {
    "municipio": "Marbella",
    "entidad": "Ayuntamiento de Marbella",
    "nif": "P2906900B",
    "actualizado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "n_expedientes": len(D) + sum(v for v in resumen["n_menores"] if v),
    "n_mayores": len(D),
    "n_menores": sum(v for v in resumen["n_menores"] if v),
    "n_menores_detalle": len(MENORES),
    "n_menores_placsp": len(PLACSP_MEN),
    "anio_min_menores_placsp": min(ANIOS_PLACSP_MEN) if ANIOS_PLACSP_MEN else None,
    "anio_min": ANIO_MIN,
    "anio_max": ANIO_MAX,
    "anio_min_menores": ANIO_MIN_MENORES,
    "importe_total": round(imp_may + imp_men, 2),
    "importe_mayores": imp_may,
    "importe_menores": imp_men,
    "ultimo_periodo": max((r["actualizado"][:10] for r in D if r.get("actualizado")), default=""),
    "organos": [o for o, _ in Counter(r["organo"] for r in D if r["organo"]).most_common()],
}

payload = {
    "meta": meta, "resumen": resumen, "tipos": tipos, "procedimientos": procedimientos,
    "estados": estados, "menores": menores, "empresas": empresas, "cpv": cpv,
    "competencia": competencia, "cobertura": cobertura,
    "busqueda": {"campos": CAMPOS, "filas": filas, "claves": claves},
}

OUT.write_text(
    "/* Generado por _scripts/build_data.py — no editar a mano. */\n"
    "window.DATOS = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
    encoding="utf-8",
)

print(f"mayores (PLACSP)        : {len(D)}  ·  {imp_may:,.0f} € con IVA")
print(f"menores (PLACSP)        : {len(PLACSP_MEN)}  ·  desde {meta['anio_min_menores_placsp']}")
print(f"menores (Ayuntamiento)  : {meta['n_menores']} certificados / {len(MENORES)} en detalle"
      f"  ·  {imp_men:,.0f} € con IVA")
print(f"periodo                 : {ANIO_MIN}-{ANIO_MAX} (menores desde {ANIO_MIN_MENORES})")
print(f"adjudicatarios distintos: {empresas['n_distintas']}")
print(f"filas en el buscador    : {len(filas)}")
print(f"data.js                 : {OUT.stat().st_size/1e6:.2f} MB")
