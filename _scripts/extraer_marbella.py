"""Extrae de los ZIP de datos abiertos de la PLACSP todos los expedientes cuyo
organo de contratacion es el Ayuntamiento de Marbella o un ente dependiente.

Salida en ../:
  contratos_marbella.json   -> dataset completo (alimenta el observatorio)
  csv/contratos_<tipo>_<anio>.csv
  csv/contratos_marbella_completo.csv
"""
import csv
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "_raw"
CSVDIR = ROOT / "csv"
CSVDIR.mkdir(exist_ok=True)

COD = json.loads((RAW / "codigos.json").read_text(encoding="utf-8"))

NIF_AYTO = "P2906900B"
DIR3_AYTO = "L01290691"
# El Ayuntamiento publica bajo varios organos (Junta de Gobierno, Alcaldia,
# Pleno...): todos se agrupan bajo la misma entidad.
PAT_AYTO = re.compile(r"(junta de gobierno|alcald|pleno|concejal).*marbella|ayuntamiento de marbella", re.I)
# Entes con perfil propio dentro del ecosistema municipal de Marbella
PAT_MARBELLA = re.compile(r"marbella", re.I)

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "cbc": "urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:dgpe:names:draft:codice:schema:xsd:CommonAggregateComponents-2",
    "cbce": "urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonBasicComponents-2",
    "cace": "urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2",
}


def txt(el, path):
    n = el.find(path, NS) if el is not None else None
    return (n.text or "").strip() if n is not None and n.text else ""


def num(s):
    try:
        return round(float(s), 2)
    except (TypeError, ValueError):
        return None


def desc(lista, code):
    if not code:
        return ""
    return COD.get(lista, {}).get(code, code)


def year_of(s):
    """Anio de una fecha ISO, descartando erratas del origen ('0019-07-18')."""
    if s and len(s) >= 4 and s[:4].isdigit():
        a = int(s[:4])
        if 2000 <= a <= 2035:
            return a
    return None


def parse_entry(el, fuente):
    cfs = el.find("cace:ContractFolderStatus", NS)
    if cfs is None:
        return None

    lcp = cfs.find("cace:LocatedContractingParty", NS)
    party = lcp.find("cac:Party", NS) if lcp is not None else None
    organo = txt(party, "cac:PartyName/cbc:Name")
    nif_org = ""
    dir3 = ""
    if party is not None:
        for pid in party.findall("cac:PartyIdentification/cbc:ID", NS):
            if pid.get("schemeName") == "NIF":
                nif_org = (pid.text or "").strip()
            elif pid.get("schemeName") == "DIR3":
                dir3 = (pid.text or "").strip()

    # jerarquia administrativa (ParentLocatedParty anidados)
    padres = []
    nodo = lcp.find("cace:ParentLocatedParty", NS) if lcp is not None else None
    while nodo is not None:
        n = txt(nodo, "cac:PartyName/cbc:Name")
        if n:
            padres.append(n)
        nodo = nodo.find("cace:ParentLocatedParty", NS)

    # --- filtro Marbella: solo por organo de contratacion / jerarquia, nunca por el objeto ---
    ambito = " | ".join([organo] + padres)
    es_ayto = (
        nif_org.upper() == NIF_AYTO
        or dir3.upper() == DIR3_AYTO
        or PAT_AYTO.search(organo or "")
    )
    if es_ayto:
        entidad = "Ayuntamiento de Marbella"
    elif PAT_MARBELLA.search(ambito):
        entidad = organo or "Marbella"
    else:
        return None

    pp = cfs.find("cac:ProcurementProject", NS)
    ba = pp.find("cac:BudgetAmount", NS) if pp is not None else None
    tp = cfs.find("cac:TenderingProcess", NS)

    cpvs = []
    if pp is not None:
        for c in pp.findall("cac:RequiredCommodityClassification/cbc:ItemClassificationCode", NS):
            if c.text:
                cpvs.append(c.text.strip())

    lugar = ""
    if pp is not None:
        lugar = txt(pp, "cac:RealizedLocation/cbc:CountrySubentity") or txt(
            pp, "cac:RealizedLocation/cac:Address/cbc:CityName"
        )

    # --- adjudicaciones (una por lote / resultado) ---
    adjs = []
    for tr in cfs.findall("cac:TenderResult", NS):
        wp = tr.find("cac:WinningParty", NS)
        atp = tr.find("cac:AwardedTenderedProject", NS)
        lmt = atp.find("cac:LegalMonetaryTotal", NS) if atp is not None else None
        adjs.append(
            {
                "lote": txt(atp, "cbc:ProcurementProjectLotID") if atp is not None else "",
                "resultado_cod": txt(tr, "cbc:ResultCode"),
                "resultado": desc("resultado", txt(tr, "cbc:ResultCode")),
                "fecha_adjudicacion": txt(tr, "cbc:AwardDate"),
                "fecha_formalizacion": txt(tr, "cac:Contract/cbc:IssueDate"),
                "n_ofertas": num(txt(tr, "cbc:ReceivedTenderQuantity")),
                "n_ofertas_pyme": num(txt(tr, "cbc:SMEsReceivedTenderQuantity")),
                "pyme_adjudicataria": txt(tr, "cbc:SMEAwardedIndicator"),
                "adjudicatario": txt(wp, "cac:PartyName/cbc:Name") if wp is not None else "",
                "nif_adjudicatario": txt(wp, "cac:PartyIdentification/cbc:ID") if wp is not None else "",
                "importe_sin_iva": num(txt(lmt, "cbc:TaxExclusiveAmount")) if lmt is not None else None,
                "importe_con_iva": num(txt(lmt, "cbc:PayableAmount")) if lmt is not None else None,
            }
        )

    link = ""
    ln = el.find("atom:link", NS)
    if ln is not None:
        link = ln.get("href", "")

    estado_cod = txt(cfs, "cbce:ContractFolderStatusCode")
    proc_cod = txt(tp, "cbc:ProcedureCode") if tp is not None else ""
    tipo_cod = txt(pp, "cbc:TypeCode") if pp is not None else ""

    imp_adj = [a["importe_sin_iva"] for a in adjs if a["importe_sin_iva"] is not None]
    fechas_adj = [a["fecha_adjudicacion"] for a in adjs if a["fecha_adjudicacion"]]

    return {
        "id": txt(el, "atom:id"),
        "expediente": txt(cfs, "cbc:ContractFolderID"),
        "objeto": txt(pp, "cbc:Name") if pp is not None else txt(el, "atom:title"),
        "entidad": entidad,
        "organo": organo,
        "nif_organo": nif_org,
        "dir3": dir3,
        "jerarquia": " > ".join(reversed(padres)),
        "fuente": fuente,  # 'mayores' | 'menores'
        "estado_cod": estado_cod,
        "estado": desc("estado", estado_cod),
        "tipo_cod": tipo_cod,
        "tipo": desc("tipo_contrato", tipo_cod),
        "procedimiento_cod": proc_cod,
        "procedimiento": desc("procedimiento", proc_cod),
        "tramitacion": desc("tramitacion", txt(tp, "cbc:UrgencyCode") if tp is not None else ""),
        "sistema": desc("sistema", txt(tp, "cbc:ContractingSystemCode") if tp is not None else ""),
        "cpv": cpvs,
        "cpv_desc": [desc("cpv", c) for c in cpvs],
        "lugar": lugar,
        "presupuesto_sin_iva": num(txt(ba, "cbc:TaxExclusiveAmount")) if ba is not None else None,
        "presupuesto_con_iva": num(txt(ba, "cbc:TotalAmount")) if ba is not None else None,
        "valor_estimado": num(txt(ba, "cbc:EstimatedOverallContractAmount")) if ba is not None else None,
        "duracion_meses": num(txt(pp, "cac:PlannedPeriod/cbc:DurationMeasure")) if pp is not None else None,
        "fecha_inicio": txt(pp, "cac:PlannedPeriod/cbc:StartDate") if pp is not None else "",
        "fecha_fin_plazo": txt(tp, "cac:TenderSubmissionDeadlinePeriod/cbc:EndDate") if tp is not None else "",
        "n_lotes": len(cfs.findall("cac:ProcurementProjectLot", NS)),
        "adjudicaciones": adjs,
        "importe_adjudicacion": round(sum(imp_adj), 2) if imp_adj else None,
        "fecha_adjudicacion": min(fechas_adj) if fechas_adj else "",
        "actualizado": txt(el, "atom:updated"),
        "enlace": link,
    }


ENTRY_RE = re.compile(r"<entry\b[^>]*>.*?</entry>", re.S)
FEED_RE = re.compile(r"<feed\b[^>]*>", re.S)

def barrer_zip(zp):
    """Devuelve los expedientes de Marbella contenidos en un ZIP anual."""
    fuente = "menores" if zp.name.startswith("menores") else "mayores"
    anio_fichero = zp.stem.split("_")[-1]
    salida, errores = [], 0
    with zipfile.ZipFile(zp) as z:
        for name in z.namelist():
            if not name.lower().endswith(".atom"):
                continue
            data = z.read(name).decode("utf-8", "replace")
            m = FEED_RE.search(data)
            feed_open = m.group() if m else "<feed>"
            for chunk in ENTRY_RE.finditer(data):
                raw = chunk.group()
                # Prefiltro barato: descarta el 99,99 % de las entradas sin
                # llegar a construir el arbol XML.
                if "arbella" not in raw and NIF_AYTO not in raw:
                    continue
                try:
                    el = ET.fromstring(feed_open + raw + "</feed>")[0]
                except ET.ParseError:
                    errores += 1
                    continue
                r = parse_entry(el, fuente)
                if r:
                    r["primer_anio_fichero"] = anio_fichero
                    salida.append(r)
    return salida, errores


# Barrer 7 GB de XML comprimido cuesta minutos, asi que el resultado de cada
# ZIP se cachea contra su tamano y su fecha: reprocesar solo lo nuevo.
CACHE = RAW / "cache"
CACHE.mkdir(exist_ok=True)

registros = {}
stats = defaultdict(int)

zips = sorted(RAW.glob("*.zip"))
print(f"{len(zips)} ficheros ZIP a procesar\n")

for zp in zips:
    st = zp.stat()
    huella = f"{st.st_size}-{int(st.st_mtime)}"
    cf = CACHE / f"{zp.stem}.json"
    hallados = None
    if cf.exists():
        try:
            guardado = json.loads(cf.read_text(encoding="utf-8"))
            if guardado.get("huella") == huella:
                hallados = guardado["registros"]
        except (json.JSONDecodeError, KeyError):
            pass
    marca = "cache" if hallados is not None else "leido"
    if hallados is None:
        hallados, errores = barrer_zip(zp)
        stats["parse_error"] += errores
        # Escritura atomica: si la extraccion se interrumpe o se solapa con
        # otra pasada, la cache nunca queda a medias.
        tmp = cf.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"huella": huella, "registros": hallados}, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(cf)

    for r in hallados:
        k = r["id"] or f"{r['expediente']}|{r['organo']}"
        prev = registros.get(k)
        if prev is None:
            registros[k] = r
        elif r["actualizado"] >= prev["actualizado"]:
            r["primer_anio_fichero"] = min(prev["primer_anio_fichero"], r["primer_anio_fichero"])
            registros[k] = r
        else:
            prev["primer_anio_fichero"] = min(prev["primer_anio_fichero"], r["primer_anio_fichero"])
    stats[zp.name] = len(hallados)
    print(f"  {zp.name:32s} -> {len(hallados):6d} coincidencias  ({marca})")

# --- anio de referencia del expediente ---
for r in registros.values():
    anio = (
        year_of(r["fecha_adjudicacion"])
        or year_of(r["fecha_fin_plazo"])
        or year_of(r["fecha_inicio"])
        or int(r["primer_anio_fichero"])
    )
    r["anio"] = anio
    r["anio_adjudicacion"] = year_of(r["fecha_adjudicacion"])

datos = sorted(registros.values(), key=lambda r: (r["anio"] or 0, r["expediente"]))

(ROOT / "contratos_marbella.json").write_text(
    json.dumps(datos, ensure_ascii=False), encoding="utf-8"
)

# --- CSV ---
CAMPOS = [
    "anio", "fuente", "expediente", "objeto", "entidad", "organo", "nif_organo",
    "tipo", "procedimiento", "tramitacion", "estado", "cpv_txt", "lugar",
    "presupuesto_sin_iva", "presupuesto_con_iva", "valor_estimado",
    "importe_adjudicacion", "adjudicatario_txt", "nif_adjudicatario_txt",
    "n_ofertas_total", "n_lotes", "duracion_meses", "fecha_inicio",
    "fecha_fin_plazo", "fecha_adjudicacion", "actualizado", "enlace",
]


def plano(r):
    ofertas = [a["n_ofertas"] for a in r["adjudicaciones"] if a["n_ofertas"]]
    d = dict(r)
    d["cpv_txt"] = "; ".join(f"{c} {n}" for c, n in zip(r["cpv"], r["cpv_desc"]))
    d["adjudicatario_txt"] = "; ".join(
        sorted({a["adjudicatario"] for a in r["adjudicaciones"] if a["adjudicatario"]})
    )
    d["nif_adjudicatario_txt"] = "; ".join(
        sorted({a["nif_adjudicatario"] for a in r["adjudicaciones"] if a["nif_adjudicatario"]})
    )
    d["n_ofertas_total"] = sum(ofertas) if ofertas else None
    return {k: d.get(k, "") for k in CAMPOS}


def escribe(path, filas):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";")
        w.writeheader()
        for r in filas:
            w.writerow(plano(r))


escribe(CSVDIR / "contratos_marbella_completo.csv", datos)
por_grupo = defaultdict(list)
for r in datos:
    por_grupo[(r["fuente"], r["anio"])].append(r)
for (fuente, anio), filas in sorted(por_grupo.items(), key=lambda x: (x[0][0], x[0][1] or 0)):
    escribe(CSVDIR / f"contratos_{fuente}_{anio}.csv", filas)

print(f"\n== {len(datos)} expedientes unicos de Marbella ==")
res_anio = defaultdict(lambda: [0, 0])
for r in datos:
    res_anio[r["anio"]][0 if r["fuente"] == "mayores" else 1] += 1
print(f"{'anio':>6} {'mayores':>8} {'menores':>8}")
for a in sorted(k for k in res_anio if k):
    print(f"{a:>6} {res_anio[a][0]:>8} {res_anio[a][1]:>8}")
print("\nJSON  ->", ROOT / "contratos_marbella.json")
print("CSV   ->", CSVDIR)
