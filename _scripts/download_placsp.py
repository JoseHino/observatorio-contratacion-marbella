"""Descarga los ficheros anuales de datos abiertos de la PLACSP (OpenPLACSP).

  - sindicacion_643  -> licitaciones (contratos mayores, excluye menores)
  - sindicacion_1143 -> contratos menores

Guarda los ZIP en _raw/. Reanuda: si el fichero ya existe y es un ZIP valido, lo salta.
"""
import concurrent.futures as cf
import pathlib
import sys
import urllib.request
import zipfile

BASE = "https://contrataciondelsectorpublico.gob.es/sindicacion"
FEEDS = {
    "licitaciones": ("sindicacion_643", "licitacionesPerfilesContratanteCompleto3"),
    "menores": ("sindicacion_1143", "contratosMenoresPerfilesContratantes"),
}
YEARS = list(range(2015, 2027))
RAW = pathlib.Path(__file__).resolve().parent.parent / "_raw"
RAW.mkdir(parents=True, exist_ok=True)

HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def ok_zip(p):
    try:
        with zipfile.ZipFile(p) as z:
            return z.namelist() != []
    except Exception:
        return False


def grab(job):
    kind, year = job
    sind, name = FEEDS[kind]
    url = f"{BASE}/{sind}/{name}_{year}.zip"
    dest = RAW / f"{kind}_{year}.zip"
    if dest.exists() and ok_zip(dest):
        return f"SKIP  {dest.name} ({dest.stat().st_size/1e6:.1f} MB ya presente)"
    tmp = dest.with_suffix(".part")
    try:
        req = urllib.request.Request(url, headers=HDRS)
        with urllib.request.urlopen(req, timeout=180) as r:
            ctype = r.headers.get("Content-Type", "")
            if "zip" not in ctype:
                return f"NODATA {kind} {year} (no publicado: {ctype})"
            with open(tmp, "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
    except Exception as e:
        if tmp.exists():
            tmp.unlink()
        return f"ERROR {kind} {year}: {type(e).__name__} {e}"
    if not ok_zip(tmp):
        tmp.unlink()
        return f"BAD   {kind} {year}: zip corrupto"
    tmp.replace(dest)
    return f"OK    {dest.name} {dest.stat().st_size/1e6:.1f} MB"


jobs = [(k, y) for k in FEEDS for y in YEARS]
with cf.ThreadPoolExecutor(max_workers=6) as ex:
    for msg in ex.map(grab, jobs):
        print(msg, flush=True)
print("== descarga terminada ==", flush=True)
