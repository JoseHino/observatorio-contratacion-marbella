"""Agrega los listados del perfil del contratante y escribe observatorio/data/data.js.

FUENTE UNICA: los documentos que el Ayuntamiento de Marbella publica en la
pestana "Documentos" de su perfil del contratante en la PLACSP, en cumplimiento
del articulo 63 de la LCSP. Los descarga descargar_perfil.py y los convierte a
datos extraer_listados.py.

  * mayores     -> Listado Anual de Contratos celebrados (indicador n 48).
                   Importes SIN IVA. 2019-2024.
  * menores     -> Relaciones trimestrales de contratos menores (y el listado
                   anual en los ejercicios sin trimestrales). CON IVA. 2018-2025.
  * modificados -> Relacion de Modificados (indicador n 50). SIN IVA. 2019-2024.

AVISO DE BASE IMPONIBLE: los listados de mayores publican el importe SIN IVA y
los de menores CON IVA, y ninguno de los dos incluye la otra base. Por eso el
observatorio NO da ninguna cifra que sume mayores y menores en euros: se
presentan siempre por separado, con su base declarada. El numero de
expedientes si es sumable, y ahi si se agregan.
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

D = json.loads((ROOT / "listados_marbella.json").read_text(encoding="utf-8"))
MAY, MEN, MOD = D["mayores"], D["menores"], D["modificados"]
PROC = D["procedencia"]

ANIOS_MAY = sorted({r["anio"] for r in MAY if r["anio"]})
ANIOS_MEN = sorted({r["anio"] for r in MEN if r["anio"]})
ANIOS_MOD = sorted({r["anio"] for r in MOD if r["anio"]})
ANIOS = sorted(set(ANIOS_MAY) | set(ANIOS_MEN))


def por_anio(filas, anios):
    d = defaultdict(list)
    for r in filas:
        d[r["anio"]].append(r)
    return [d.get(a, []) for a in anios]


def serie(filas, anios, f):
    return [f(rs) for rs in por_anio(filas, anios)]


def suma(campo):
    return lambda rs: round(sum(r.get(campo) or 0 for r in rs), 2) or None


def cuenta(rs):
    return len(rs) or None


def limpia(s):
    return " ".join(str(s or "").split())


# La fecha de publicacion viene como "19 Aug 2026", con el mes en ingles. Sin
# convertirla, ordenar por texto dice que el ultimo documento es de diciembre.
MESES = {m: i for i, m in enumerate(
    "jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}


def fecha_pub(s):
    p = limpia(s).split()
    if len(p) == 3 and p[1][:3].lower() in MESES and p[0].isdigit():
        return f"{p[2]}-{MESES[p[1][:3].lower()]:02d}-{int(p[0]):02d}"
    return ""


def _sin_tildes(s):
    s = unicodedata.normalize("NFKD", limpia(s).lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def tipo_contrato(s):
    """Unifica el tipo de contrato, que el listado escribe como le parece.

    No es fusionar por parecido: el tipo es un vocabulario cerrado de la LCSP y
    los listados lo escriben en singular y en plural indistintamente
    ("Servicio"/"Servicios", "Obra"/"Obras"), con alguna errata de volcado
    ("Sevicios", "Esuministro"). Sin unificar, en contratos menores el top de
    tipos salia Servicios/Servicio/Suministro/Suministros y OBRAS NO APARECIA
    EN NINGUNA GRAFICA.

    Lo que no se reconoce se deja tal cual, a la vista, en vez de esconderlo en
    un "Otros": si en la columna de tipo aparece un procedimiento —pasa en unas
    pocas filas de un PDF con las columnas descuadradas— hay que poder verlo.
    """
    t = _sin_tildes(s)
    if not t:
        return ""
    if "obra" in t:
        return "Obras"
    if "suministr" in t:
        return "Suministros"
    if "servicio" in t or "sevicio" in t:
        return "Servicios"
    if "patrimonial" in t:
        return "Patrimonial"
    if "administrativo especial" in t:
        return "Administrativo especial"
    if "privado" in t:
        return "Privado"
    return limpia(s).title()


def procedimiento(s):
    """Mismo criterio para el procedimiento: 'Engarco a medios propios' es la
    misma figura que 'Encargo a medio propio', y 'Simplificado sumario' es el
    'Abierto simplificado sumario' escrito corto."""
    t = _sin_tildes(s)
    if not t:
        return ""
    if "encargo" in t or "engarco" in t:
        return "Encargo a medio propio"
    if "sumario" in t:
        return "Abierto simplificado sumario"
    if "simplificado" in t:
        return "Abierto simplificado"
    if "negociado" in t:
        return "Negociado sin publicidad"
    if t.startswith("abierto"):
        return "Abierto"
    if "emergencia" in t:
        return "Emergencia"
    return limpia(s).title()


def titulo_empresa(s):
    """Los nombres vienen tal cual los publica el Ayuntamiento: la misma
    empresa aparece con grafias distintas. Se normaliza lo evidente (espacios,
    puntuacion final, mayusculas) y nada mas: fusionar por parecido seria
    inventar adjudicatarios."""
    return limpia(s).rstrip(" .,;").upper()


# ===========================================================  PANORAMA  ====
resumen = {
    "x": ANIOS,
    "n_mayores": serie(MAY, ANIOS, cuenta),
    "n_menores": serie(MEN, ANIOS, cuenta),
    "imp_mayores": serie(MAY, ANIOS, suma("importe_adjudicacion")),
    "lic_mayores": serie(MAY, ANIOS, suma("importe_licitacion")),
    "imp_menores": serie(MEN, ANIOS, suma("importe_con_iva")),
    "pct_menores_num": [],
}
for i, a in enumerate(ANIOS):
    nm, nM = resumen["n_menores"][i], resumen["n_mayores"][i]
    resumen["pct_menores_num"].append(
        round(nm / (nm + nM) * 100, 1) if nm and nM else None)

# La "baja de adjudicacion" NO se puede calcular con este listado.
#
# Hasta 2021 el importe de adjudicacion era menor que el de licitacion en casi
# todas las filas, como cabe esperar. A partir de 2022 el Ayuntamiento rellena
# la columna de importe de licitacion con otro criterio y la adjudicacion pasa
# a superarla en una parte creciente de los expedientes: 38,6 % en 2022,
# 44,6 % en 2023 y 60,5 % en 2024. Agregado, 2024 daria una baja de -1,5 %,
# que presentada como indicador de eficiencia es sencillamente falsa.
#
# Asi que en vez de una baja se publica el desajuste, que si es un hecho
# comprobable y ademas dice algo sobre la calidad de lo publicado.
anomalia = {"x": ANIOS, "n": [], "pct": [], "con_ambas": []}
for rs in por_anio(MAY, ANIOS):
    par = [(r["importe_licitacion"], r["importe_adjudicacion"]) for r in rs
           if r.get("importe_licitacion") and r.get("importe_adjudicacion")]
    n = sum(1 for lic, adj in par if adj > lic)
    anomalia["con_ambas"].append(len(par) or None)
    anomalia["n"].append(n or None)
    anomalia["pct"].append(round(n / len(par) * 100, 1) if par else None)
resumen["adj_supera_lic"] = anomalia["pct"]

# ============================================================  MAYORES  ====
TIPOS_MAY = [t for t, _ in Counter(tipo_contrato(r["tipo"]) for r in MAY
                                   if tipo_contrato(r["tipo"])).most_common(6)]
PROCS = [p for p, _ in Counter(procedimiento(r["procedimiento"]) for r in MAY
                               if procedimiento(r["procedimiento"])).most_common(6)]


def _norm_campo(campo):
    return tipo_contrato if campo == "tipo" else procedimiento


def reparto(filas, anios, campo, valores):
    f = _norm_campo(campo)
    return [serie(filas, anios,
                  lambda rs, v=v: sum(1 for r in rs if f(r[campo]) == v) or None)
            for v in valores]


def reparto_imp(filas, anios, campo, valores, imp):
    f = _norm_campo(campo)
    return [serie(filas, anios,
                  lambda rs, v=v: round(sum(r.get(imp) or 0 for r in rs
                                            if f(r[campo]) == v), 2) or None)
            for v in valores]


mayores = {
    "x": ANIOS_MAY,
    "tipos": TIPOS_MAY,
    "n_tipo": reparto(MAY, ANIOS_MAY, "tipo", TIPOS_MAY),
    "imp_tipo": reparto_imp(MAY, ANIOS_MAY, "tipo", TIPOS_MAY, "importe_adjudicacion"),
    "procedimientos": PROCS,
    "n_proc": reparto(MAY, ANIOS_MAY, "procedimiento", PROCS),
    "imp_proc": reparto_imp(MAY, ANIOS_MAY, "procedimiento", PROCS, "importe_adjudicacion"),
    "licitacion": serie(MAY, ANIOS_MAY, suma("importe_licitacion")),
    "adjudicado": serie(MAY, ANIOS_MAY, suma("importe_adjudicacion")),
    "importe_medio": [],
    "n_lotes": sum(1 for r in MAY if limpia(r.get("lote"))),
}
for rs in por_anio(MAY, ANIOS_MAY):
    v = [r["importe_adjudicacion"] for r in rs if r.get("importe_adjudicacion")]
    mayores["importe_medio"].append(round(sum(v) / len(v), 2) if v else None)

# =========================================================  COMPETENCIA  ===
# POR EXPEDIENTE, NO POR FILA. El listado trae una fila por lote y por
# adjudicatario: los expedientes patrimoniales de la feria (puestos de
# alimentacion, casetas de juegos) repiten el mismo expediente decenas de veces
# con el total de solicitantes en cada fila. Contando filas, la media de
# licitadores de 2024 salia 26,4; por expediente son 4,5, que es la cifra real.
#
# El n de licitadores solo esta relleno en parte de los expedientes: los
# indicadores se calculan sobre los informados y se publica cuantos son.
def expedientes_con_licitadores(rs):
    """{expediente: n licitadores}. Si una fila del mismo expediente trae un
    numero distinto se queda el mayor: el campo es del expediente, no del lote."""
    out = {}
    for r in rs:
        k = limpia(r.get("expediente")).upper()
        n = r.get("n_licitadores")
        if k and isinstance(n, int) and n > 0:
            out[k] = max(out.get(k, 0), n)
    return out


competencia = {"x": ANIOS_MAY, "media": [], "pct_una": [],
               "informados": [], "pct_informados": [], "expedientes": []}
for rs in por_anio(MAY, ANIOS_MAY):
    todos = {limpia(r.get("expediente")).upper() for r in rs if limpia(r.get("expediente"))}
    con = expedientes_con_licitadores(rs)
    v = list(con.values())
    competencia["expedientes"].append(len(todos) or None)
    competencia["media"].append(round(sum(v) / len(v), 1) if v else None)
    competencia["pct_una"].append(
        round(sum(1 for x in v if x == 1) / len(v) * 100, 1) if v else None)
    competencia["informados"].append(len(v) or None)
    competencia["pct_informados"].append(
        round(len(v) / len(todos) * 100, 1) if todos else None)

# ============================================================  MENORES  ====
TIPOS_MEN = [t for t, _ in Counter(tipo_contrato(r["tipo"]) for r in MEN
                                   if tipo_contrato(r["tipo"])).most_common(4)]
menores = {
    "x": ANIOS_MEN,
    "tipos": TIPOS_MEN,
    "n_tipo": reparto(MEN, ANIOS_MEN, "tipo", TIPOS_MEN),
    "imp_tipo": reparto_imp(MEN, ANIOS_MEN, "tipo", TIPOS_MEN, "importe_con_iva"),
    "importe_medio": [],
    "trimestres": {"x": ["T1", "T2", "T3", "T4"], "anios": [], "n": [], "importe": []},
}
for rs in por_anio(MEN, ANIOS_MEN):
    v = [r["importe_con_iva"] for r in rs if r.get("importe_con_iva")]
    menores["importe_medio"].append(round(sum(v) / len(v), 2) if v else None)

# El trimestre solo existe donde hay relacion trimestral publicada.
for a in ANIOS_MEN:
    rs = [r for r in MEN if r["anio"] == a and r.get("trimestre")]
    if not rs:
        continue
    n, imp = [0, 0, 0, 0], [0.0, 0.0, 0.0, 0.0]
    for r in rs:
        t = r["trimestre"] - 1
        n[t] += 1
        imp[t] += r.get("importe_con_iva") or 0
    menores["trimestres"]["anios"].append(a)
    menores["trimestres"]["n"].append(n)
    menores["trimestres"]["importe"].append([round(x, 2) for x in imp])

# ========================================================  MODIFICADOS  ====
modificados = {
    "x": ANIOS_MOD,
    "n": serie(MOD, ANIOS_MOD, cuenta),
    "importe": serie(MOD, ANIOS_MOD, suma("importe_modificacion")),
    "pct_sobre_adjudicado": [],
}
adj_may = dict(zip(ANIOS_MAY, mayores["adjudicado"]))
for i, a in enumerate(ANIOS_MOD):
    imp, base = modificados["importe"][i], adj_may.get(a)
    modificados["pct_sobre_adjudicado"].append(
        round(imp / base * 100, 2) if imp and base else None)

top_mod = sorted([r for r in MOD if r.get("importe_modificacion")],
                 key=lambda r: -r["importe_modificacion"])[:12]
modificados["top"] = {
    "x": [f"{limpia(r['expediente'])} · {r['anio']}" for r in top_mod][::-1],
    "v": [r["importe_modificacion"] for r in top_mod][::-1],
}

# ======================================================  ADJUDICATARIOS  ===
# Mayores y menores NO se suman en euros (bases de IVA distintas): dos
# rankings separados y un recuento conjunto de expedientes, que si es sumable.
def ranking(filas, imp, n=15):
    tot_i, tot_n = defaultdict(float), Counter()
    for r in filas:
        nom = titulo_empresa(r.get("adjudicatario"))
        if not nom:
            continue
        tot_i[nom] += r.get(imp) or 0
        tot_n[nom] += 1
    top = sorted(tot_i.items(), key=lambda kv: -kv[1])[:n]
    return ({"x": [k for k, _ in top][::-1], "v": [round(v, 2) for _, v in top][::-1]},
            tot_i, tot_n)


top_may, emp_may_i, emp_may_n = ranking(MAY, "importe_adjudicacion")
top_men, emp_men_i, emp_men_n = ranking(MEN, "importe_con_iva")
n_conjunto = Counter()
n_conjunto.update(emp_may_n)
n_conjunto.update(emp_men_n)
top_num = n_conjunto.most_common(15)

empresas = {
    "top_mayores": top_may,
    "top_menores": top_men,
    "top_numero": {"x": [k for k, _ in top_num][::-1], "v": [v for _, v in top_num][::-1]},
    "n_distintas": len(set(emp_may_i) | set(emp_men_i)),
    "n_solo_mayores": len(emp_may_i),
    "n_solo_menores": len(emp_men_i),
    "n_en_ambos": len(set(emp_may_i) & set(emp_men_i)),
    "concentracion_may": round(
        sum(v for _, v in sorted(emp_may_i.items(), key=lambda kv: -kv[1])[:10])
        / (sum(emp_may_i.values()) or 1) * 100, 1),
}

# ==========================================================  BUSCADOR  =====
CAMPOS = ["a", "cl", "ex", "ob", "ti", "pr", "adj", "nif", "imp", "lic", "f", "doc", "url"]


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


filas = []
for r in MAY:
    filas.append([r["anio"], "m", limpia(r["expediente"]), limpia(r["objeto"])[:400],
                  tipo_contrato(r["tipo"]), procedimiento(r["procedimiento"]),
                  limpia(r["adjudicatario"]), limpia(r.get("nif_adjudicatario")),
                  r.get("importe_adjudicacion"), r.get("importe_licitacion"),
                  r.get("fecha_formalizacion") or "", r["documento"], r["url_documento"]])
for r in MEN:
    ref = limpia(r["expediente"]) or limpia(r.get("n_contrato"))
    filas.append([r["anio"], "M", ref, limpia(r["objeto"])[:400],
                  tipo_contrato(r["tipo"]), "Contrato menor",
                  limpia(r["adjudicatario"]), limpia(r.get("nif_adjudicatario")),
                  r.get("importe_con_iva"), None,
                  "", r["documento"], r["url_documento"]])
for r in MOD:
    filas.append([r["anio"], "x", limpia(r["expediente"]), limpia(r["objeto"])[:400],
                  tipo_contrato(r["tipo"]), "Modificación",
                  limpia(r["adjudicatario"]), limpia(r.get("nif_adjudicatario")),
                  r.get("importe_modificacion"), None,
                  r.get("fecha_formalizacion") or "", r["documento"], r["url_documento"]])

filas.sort(key=lambda f: (-(f[0] or 0), f[2] or ""))
claves = [norm(" ".join(str(f[i] or "") for i in (2, 3, 6, 7))) for f in filas]

# ==============================================================  META  =====
meta = {
    "municipio": "Marbella",
    "entidad": "Ayuntamiento de Marbella",
    "nif": "P2906900B",
    "actualizado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "n_mayores": len(MAY),
    "n_menores": len(MEN),
    "n_modificados": len(MOD),
    "n_expedientes": len(MAY) + len(MEN),
    "anio_min": min(ANIOS), "anio_max": max(ANIOS),
    "anio_min_may": min(ANIOS_MAY), "anio_max_may": max(ANIOS_MAY),
    "anio_min_men": min(ANIOS_MEN), "anio_max_men": max(ANIOS_MEN),
    "anio_min_mod": min(ANIOS_MOD), "anio_max_mod": max(ANIOS_MOD),
    "imp_mayores": round(sum(r.get("importe_adjudicacion") or 0 for r in MAY), 2),
    "imp_menores": round(sum(r.get("importe_con_iva") or 0 for r in MEN), 2),
    "imp_modificados": round(sum(r.get("importe_modificacion") or 0 for r in MOD), 2),
    "n_documentos": len(PROC),
    "ultimo_documento": max((fecha_pub(d["publicado"]) for d in PROC), default=""),
    "documentos": sorted(
        ({"clase": d["clase"], "anio": d["anio"], "trimestre": d["trimestre"],
          "titulo": d["titulo"], "publicado": fecha_pub(d["publicado"]),
          "url": d["url"], "filas": d["filas"]} for d in PROC),
        key=lambda d: (d["clase"], d["anio"] or 0, d["trimestre"] or 0)),
}

payload = {
    "meta": meta, "resumen": resumen, "mayores": mayores, "menores": menores,
    "modificados": modificados, "competencia": competencia, "anomalia": anomalia,
    "empresas": empresas,
    "busqueda": {"campos": CAMPOS, "filas": filas, "claves": claves},
}

OUT.write_text(
    "/* Generado por _scripts/build_data.py — no editar a mano. */\n"
    "window.DATOS = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
    encoding="utf-8")

print(f"mayores      : {len(MAY):5d}  {min(ANIOS_MAY)}-{max(ANIOS_MAY)}  ·  {meta['imp_mayores']:,.0f} € sin IVA")
print(f"menores      : {len(MEN):5d}  {min(ANIOS_MEN)}-{max(ANIOS_MEN)}  ·  {meta['imp_menores']:,.0f} € con IVA")
print(f"modificados  : {len(MOD):5d}  {min(ANIOS_MOD)}-{max(ANIOS_MOD)}  ·  {meta['imp_modificados']:,.0f} € sin IVA")
print(f"adjudicatarios distintos: {empresas['n_distintas']}")
print(f"filas en el buscador    : {len(filas)}")
print(f"documentos fuente       : {len(PROC)}  (ultimo publicado {meta['ultimo_documento']})")
print(f"data.js                 : {OUT.stat().st_size/1e6:.2f} MB")
