# Observatorio de Transparencia en la Contratación · Ayuntamiento de Marbella

Contratos **mayores y menores** del Ayuntamiento de Marbella, presentados como
observatorio web con buscador de expedientes.

**Panel:** https://josehino.github.io/observatorio-contratacion-marbella/

---

## Fuentes (enlace directo a cada una)

| Dato | Fuente | Enlace directo |
|---|---|---|
| Contratos **mayores** | Plataforma de Contratación del Sector Público · datos abiertos (fichero anual `licitacionesPerfilesContratanteCompleto3`) | https://contrataciondelsectorpublico.gob.es/wps/portal/DatosAbiertos |
| Contratos **menores** | Ayuntamiento de Marbella · Portal de Información Pública → Contratación pública | https://informacionpublica.marbella.es/ambitos/gestion-economica-y-administrativa/contratacion-publica.html |
| Ficha de cada expediente | PLACSP · buscador de licitaciones | https://contrataciondelestado.es/wps/portal/licitaciones |
| Perfil del contratante | Ayuntamiento de Marbella | https://ayuntamiento.marbella.es/oferta-publica/perfil-del-contratante.html |
| Especificación de los datos | Guía OpenPLACSP (PDF) | https://contrataciondelestado.es/datosabiertos/DGPE_PLACSP_OpenPLACSP_v.1.3.pdf |
| Códigos CODICE (tipos, procedimientos, CPV) | PLACSP | https://contrataciondelestado.es/codice/cl/ |

En el panel, **cada gráfica lleva debajo el enlace a su fuente** y cada
expediente mayor del buscador enlaza a su ficha en la Plataforma.

> **Los contratos menores están en dos sitios que no dicen lo mismo.** El
> Ayuntamiento los publica en la PLACSP **desde 2022** (2.655 expedientes, cada
> uno con su ficha) y, en paralelo, certifica un **total anual propio** en su
> relación de contratos menores, que llega hasta 2020 y cubre años que la
> Plataforma no tiene. Las dos cifras no coinciden: la PLACSP recoge entre el
> 83 % y el 100 % de lo certificado, según el año.
>
> Las **gráficas agregadas usan el total certificado**, que es la cifra que el
> Ayuntamiento firma. El **buscador usa el detalle de la PLACSP** donde lo hay y
> el listado municipal en los años en que la PLACSP no trae nada —nunca los dos
> a la vez, que serían el mismo contrato dos veces—. La diferencia se publica
> como **indicador de cobertura** en la sección de contratos menores.
>
> Todos los importes van **con IVA**: es la única base común, porque el listado
> municipal de menores solo publica el importe con IVA.

## Cobertura de la PLACSP sobre lo certificado

| Año | Certificado por el Ayto. | En la PLACSP | Cobertura (nº) |
|---|---|---|---|
| 2021 | 693 · 5,13 M€ | — | la PLACSP no trae ninguno |
| 2022 | 677 · 4,35 M€ | 647 · 4,48 M€ | 95,6 % |
| 2023 | 616 · 4,24 M€ | 545 · 3,68 M€ | 88,5 % |
| 2024 | 553 · 3,98 M€ | 492 · 3,33 M€ | 89,0 % |
| 2025 | 621 · 4,70 M€ | 577 · 3,88 M€ | 92,9 % |

---

## Qué hay en este repositorio

| Ruta | Qué es |
|---|---|
| `observatorio/` | El panel. Chasis del kit en `assets/`, declaración en `app.js`, datos en `data/data.js`. |
| `index.html` | Redirección a `observatorio/` para GitHub Pages. |
| `csv/` | Un CSV por año de los contratos mayores más el consolidado `contratos_marbella_completo.csv`. Separador `;` y BOM: se abren en Excel con doble clic. |
| `contratos_marbella.json` | Contratos mayores con todo el detalle, incluidas las adjudicaciones lote a lote. |
| `menores_marbella.json` | Contratos menores: totales certificados por el Ayuntamiento y listado de detalle. |
| `_scripts/` | El pipeline. |

Los ZIP anuales descargados de la PLACSP (`_raw/`, varios GB) y las capturas de
verificación no se versionan: se regeneran con el pipeline.

## El pipeline, en orden

```bash
python _scripts/download_placsp.py      # 1. descarga los ZIP anuales (reanudable)
python _scripts/codigos.py              # 2. listas de códigos CODICE (tipos, CPV…)
python _scripts/extraer_marbella.py     # 3. MAYORES: filtra Marbella -> JSON + CSV
python _scripts/menores_ayto.py         # 4. MENORES: lee los listados del Ayuntamiento
python _scripts/build_data.py           # 5. agrega -> observatorio/data/data.js
python _scripts/empaquetar_html.py      # 6. empaqueta el HTML único
python _scripts/verificar.py            # 7. comprueba que TODAS las gráficas pintan
```

Los pasos 1 y 3 son incrementales: el descargador salta los ZIP ya presentes y
válidos, y el extractor cachea el resultado de cada ZIP contra su tamaño y
fecha. Añadir un año nuevo cuesta minutos, no la descarga entera.

## Cómo se selecciona "Marbella"

Por **órgano de contratación**, nunca por el objeto del contrato —si no,
entrarían las obras de otras administraciones ejecutadas en Marbella:

- NIF `P2906900B` o DIR3 `L01290691` → *Ayuntamiento de Marbella*. El
  Ayuntamiento publica indistintamente como Junta de Gobierno, Alcaldía o
  Pleno; los tres se agrupan bajo la misma entidad.
- Cualquier otro órgano cuyo nombre o jerarquía contenga «Marbella» se recoge
  también, con su nombre propio, para no perder los entes municipales
  dependientes.

Cada expediente aparece una sola vez: si figura en varios ficheros anuales
—porque se publicó un año y se adjudicó al siguiente— se conserva la versión
con el `updated` más reciente.

## Qué contiene cada registro

Identificación (expediente, órgano, NIF, DIR3), objeto, tipo de contrato,
procedimiento, tramitación, estado, CPV con su descripción oficial, lugar de
ejecución, presupuesto base sin y con IVA, valor estimado, duración, número de
lotes, enlace a la ficha de la Plataforma y **una entrada por adjudicación**
con lote, resultado, fecha, número de ofertas recibidas, ofertas de PYME,
adjudicatario, NIF e importe.

## Los contratos menores, en detalle

Los listados municipales traen **dos cosas que no cuadran entre sí**:

- Una tabla de **totales certificados** por año, tipo y trimestre (2021-2025).
- Un **listado contrato a contrato** (2020-2025), volcado desde PDF, con líneas
  partidas y repetidas: da entre un 5 % y un 10 % más de filas e importe que el
  total certificado del mismo año.

El observatorio no promedia esa diferencia ni elige en silencio: las **gráficas
agregadas usan el total certificado** y el **buscador usa el detalle**, y la
propia sección de menores lo advierte. Para 2020 no hay total certificado, así
que ese año se agrega desde el detalle.

## Limitaciones que hay que decir al cliente

- El observatorio refleja **lo publicado**. Un expediente tramitado y no
  publicado no aparece.
- Los indicadores de competencia (ofertas por licitación, adjudicaciones con
  una sola oferta) se calculan solo sobre los expedientes en los que el órgano
  de contratación rellenó ese campo, que no son todos.
- La Plataforma **ofusca el NIF de las personas físicas**, así que un mismo
  autónomo puede aparecer sin identificador completo.
- El año en curso es un ejercicio abierto: sus cifras no se comparan con las de
  un año completo. El panel lo advierte en cada tarjeta.
- El año de referencia de un expediente es el de su adjudicación; si no consta,
  el del fin de plazo de presentación, y en último término el del fichero anual
  en el que apareció por primera vez.

---

Consultoría **AMMA Consulting** para el Ayuntamiento de Marbella · Marbella DTI.
Todos los datos proceden de fuentes públicas oficiales, enlazadas arriba.
