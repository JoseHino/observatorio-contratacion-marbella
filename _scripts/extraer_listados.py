"""Convierte los PDF del perfil del contratante en datos.

Entrada : _raw/perfil/*.pdf + _raw/perfil/inventario.json (los escribe
          descargar_perfil.py descargando del perfil del Ayuntamiento).
Salida  : listados_marbella.json y csv/*.csv

Tres familias de documento, cada una con su tabla:

  * mayores      -> Listado Anual de Contratos celebrados (indicador n 48).
                    Importes SIN IVA. 2019 en adelante.
  * menores      -> Relaciones trimestrales y anuales de contratos menores.
                    Importes CON IVA. 2018 en adelante.
  * modificados  -> Relacion de Modificados (indicador n 50). Importe de la
                    modificacion, SIN IVA.

Las columnas NO estan en el mismo orden en todos los anos —2023 movio "orden"
detras del NIF, 2019 escribia "Nº Expediente Clave" y 2020 partia
"A dministracion"—, asi que cada columna se localiza por su nombre
normalizado y no por su posicion. Si una columna esperada no aparece, el
documento se salta con un aviso en vez de producir datos torcidos.

En los contratos menores mandan las relaciones TRIMESTRALES: su suma coincide
con los totales que el Ayuntamiento certifica, mientras que algun listado
anual trae filas de mas. El listado anual solo se usa en los ejercicios sin
relaciones trimestrales publicadas.
"""
import csv
import json
import pathlib
import re
import sys
import unicodedata
from collections import defaultdict

import pdfplumber

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "_raw" / "perfil"
OUT = ROOT / "listados_marbella.json"
CSV = ROOT / "csv"


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def compacta(s):
    """Cabecera sin espacios. Los PDF parten las palabras al maquetar:
    "Ejercici o", "A dministracion", "Duració n", "F ec h a d e fo rm"...
    Comparar sin espacios es lo unico que aguanta los ocho ejercicios."""
    return norm(s).replace(" ", "")


def num(v):
    """Importe europeo tolerante: 1.234,56 / 1234,56 / 1.234 / 1234.56."""
    s = re.sub(r"[^\d,.\-]", "", str(v or ""))
    if not s or s in {"-", ".", ","}:
        return None
    if re.search(r",\d{1,2}$", s):
        s = s.replace(".", "").replace(",", ".")
    elif re.search(r"\.\d{3}(?:\D|$)", s) and not re.search(r"\.\d{1,2}$", s):
        s = s.replace(".", "")
    else:
        s = s.replace(",", "")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def fecha(v):
    """Devuelve ISO. Acepta 12/03/2024, 12-03-24 y '2024-03-12 00:00:00'."""
    s = str(v or "").strip()
    if not s:
        return ""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.match(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", s)
    if m:
        d, mes, a = m.groups()
        a = a if len(a) == 4 else "20" + a
        return f"{a}-{int(mes):02d}-{int(d):02d}"
    return ""


def entero(v):
    m = re.search(r"\d+", str(v or ""))
    return int(m.group()) if m else None


# Cada campo se busca por los comienzos de cabecera con los que aparece en
# alguno de los anos. El orden importa: gana la primera que case.
CAMPOS = {
    "mayores": {
        "ejercicio": ["ejercicio"],
        "orden": ["no orden", "orden"],
        "nif_organo": ["n.i.f."],
        "administracion": ["administracion", "a dministracion"],
        "expediente": ["expediente clave", "no expediente clav", "no expediente"],
        "objeto": ["descripcion del co"],
        "tipo": ["tipo de contrato"],
        "lote": ["no de lote"],
        "procedimiento": ["procedimiento de a"],
        "n_licitadores": ["no licitadores"],
        "importe_licitacion": ["importe licitacion"],
        "importe_adjudicacion": ["imp. adjudicacion", "imp adjudicacion"],
        "nif_adjudicatario": ["n.i.f. adjudicatar"],
        "adjudicatario": ["adjudicatario (nom"],
        "fecha_formalizacion": ["fecha formaliza", "fecha de form"],
    },
    "menores": {
        "ejercicio": ["ejercicio"],
        "nif_organo": ["n.i.f. entidad rem", "n.i.f."],
        "entidad": ["entidad remitente"],
        "expediente": ["no expediente", "expediente"],
        "n_contrato": ["no de contrato"],
        "objeto": ["descripcion del co"],
        "tipo": ["tipo de contrato", "tipo de"],
        "nif_adjudicatario": ["n.i.f. adjudicatar"],
        "adjudicatario": ["adjudicatario (nom"],
        "duracion": ["duracion"],
        "importe_con_iva": ["importe adjudicacion", "importe"],
    },
    "modificados": {
        "ejercicio": ["ejercicio"],
        "orden": ["no orden", "orden"],
        "nif_organo": ["n.i.f."],
        "expediente": ["no expediente", "expediente"],
        "objeto": ["descripcion del co"],
        "tipo": ["tipo de contrato"],
        "fecha_aprobacion": ["fecha de aprobacio"],
        "importe_modificacion": ["importe modificaci"],
        "variacion_plazo": ["variacion de plazo"],
        "nif_adjudicatario": ["n.i.f. adjudicatar"],
        "adjudicatario": ["adjudicatario (nom"],
        "fecha_formalizacion": ["fecha formalizacio", "fecha de formaliza"],
    },
}

NUMERICOS = {"importe_licitacion", "importe_adjudicacion", "importe_con_iva",
             "importe_modificacion"}
FECHAS = {"fecha_formalizacion", "fecha_aprobacion"}
ENTEROS = {"n_licitadores", "orden"}


def mapear(cabecera, clase):
    """Posicion de cada campo dentro de la fila, por nombre de cabecera."""
    cols = [compacta(c) for c in cabecera]
    mapa = {}
    for campo, alias in CAMPOS[clase].items():
        for a in (compacta(x) for x in alias):
            for i, c in enumerate(cols):
                if c.startswith(a) and i not in mapa.values():
                    mapa[campo] = i
                    break
            if campo in mapa:
                break
    return mapa


def leer(path, clase):
    """Filas de un PDF. La cabecera puede repetirse en cada pagina."""
    filas, mapa, avisos = [], None, 0
    with pdfplumber.open(path) as pdf:
        for pg in pdf.pages:
            for tabla in pg.extract_tables():
                for fila in tabla:
                    celdas = [(c or "").replace("\n", " ").strip() for c in fila]
                    if not any(celdas):
                        continue
                    if compacta(celdas[0]) == "ejercicio":
                        mapa = mapear(celdas, clase)
                        continue
                    if not re.fullmatch(r"\d{4}", celdas[0] or ""):
                        continue
                    if mapa is None:
                        avisos += 1
                        continue
                    r = {}
                    for campo, i in mapa.items():
                        v = celdas[i] if i < len(celdas) else ""
                        if campo in NUMERICOS:
                            r[campo] = num(v)
                        elif campo in FECHAS:
                            r[campo] = fecha(v)
                        elif campo in ENTEROS:
                            r[campo] = entero(v)
                        else:
                            r[campo] = v
                    r["ejercicio"] = entero(r.get("ejercicio"))
                    filas.append(r)
    return filas, mapa, avisos


def main():
    inv = json.loads((RAW / "inventario.json").read_text(encoding="utf-8"))
    datos = {"mayores": [], "menores": [], "modificados": []}
    procedencia = []

    # --- menores: mandan los trimestrales; el anual solo rellena huecos ----
    trimestrales = defaultdict(list)
    anuales = {}
    for d in inv:
        if d["clase"] != "menores":
            continue
        (trimestrales[d["anio"]].append(d) if d["trimestre"] else
         anuales.setdefault(d["anio"], d))

    for d in sorted(inv, key=lambda x: (x["clase"], x["anio"] or 0, x["trimestre"] or 0)):
        clase, a, t = d["clase"], d["anio"], d["trimestre"]
        if clase == "menores" and not t and trimestrales.get(a):
            print(f"  OMITE  {d['fichero'][:52]:52s} (hay relaciones trimestrales de {a})")
            continue

        filas, mapa, avisos = leer(RAW / d["fichero"], clase)
        faltan = set(CAMPOS[clase]) - set(mapa or {})
        if not filas:
            print(f"  VACIO  {d['fichero'][:52]:52s} SIN FILAS")
            continue
        for r in filas:
            r["anio"] = a
            r["trimestre"] = t
            r["documento"] = d["titulo"]
            r["url_documento"] = d["url"]
            r["publicado"] = d["publicado"]
        datos[clase].extend(filas)
        procedencia.append({k: d[k] for k in
                            ("clase", "anio", "trimestre", "complementario",
                             "titulo", "publicado", "url", "fichero")} |
                           {"filas": len(filas)})
        extra = f"  faltan={sorted(faltan)}" if faltan else ""
        aviso = f"  sin-cabecera={avisos}" if avisos else ""
        print(f"  OK     {d['fichero'][:52]:52s} {len(filas):5d} filas{extra}{aviso}")

    OUT.write_text(json.dumps({"procedencia": procedencia, **datos},
                              ensure_ascii=False), encoding="utf-8")

    CSV.mkdir(exist_ok=True)
    for clase, filas in datos.items():
        if not filas:
            continue
        campos = list(CAMPOS[clase]) + ["anio", "trimestre", "documento", "publicado", "url_documento"]
        with open(CSV / f"{clase}_marbella.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
            w.writeheader()
            w.writerows(filas)

    print("\n== resumen ==")
    for clase, filas in datos.items():
        por_anio = defaultdict(int)
        for r in filas:
            por_anio[r["anio"]] += 1
        print(f"  {clase:12s} {len(filas):6d} filas   " +
              " ".join(f"{a}:{n}" for a, n in sorted(por_anio.items())))
    print(f"\nJSON -> {OUT}")
    print(f"CSV  -> {CSV}")


if __name__ == "__main__":
    main()
