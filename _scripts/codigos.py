"""Descarga las listas de codigos CODICE (genericode) y las deja como dict code -> nombre es."""
import json
import pathlib
import urllib.request
import xml.etree.ElementTree as ET

OUT = pathlib.Path(__file__).resolve().parent.parent / "_raw" / "codigos.json"
BASE = "https://contrataciondelestado.es/codice/cl"
HDRS = {"User-Agent": "Mozilla/5.0"}

LISTAS = {
    "tipo_contrato": "2.08/ContractCode-2.08.gc",
    "procedimiento": "2.07/SyndicationTenderingProcessCode-2.07.gc",
    "resultado": "2.09/TenderResultCode-2.09.gc",
    "estado": "2.04/SyndicationContractFolderStatusCode-2.04.gc",
    "tramitacion": "1.04/DiligenceTypeCode-1.04.gc",
    "sistema": "2.08/ContractingSystemTypeCode-2.08.gc",
    "cpv": "2.04/CPV2008-2.04.gc",
}


def parse_gc(data):
    root = ET.fromstring(data)
    out = {}
    for row in root.iter("Row"):
        vals = {}
        for v in row.findall("Value"):
            col = v.get("ColumnRef")
            s = v.find("SimpleValue")
            vals[col] = (s.text or "").strip() if s is not None else ""
        code = vals.get("code") or vals.get("Code")
        nombre = vals.get("nombre") or vals.get("name") or vals.get("Nombre")
        if code:
            out[code] = nombre or code
    return out


res = {}
for key, path in LISTAS.items():
    try:
        req = urllib.request.Request(f"{BASE}/{path}", headers=HDRS)
        with urllib.request.urlopen(req, timeout=90) as r:
            res[key] = parse_gc(r.read())
        print(f"{key}: {len(res[key])} codigos")
    except Exception as e:
        print(f"{key}: ERROR {e}")
        res[key] = {}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("->", OUT)
