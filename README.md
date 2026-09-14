# Observatorio de Transparencia en la Contratación · Ayuntamiento de Marbella

Contratos **mayores y menores** del Ayuntamiento de Marbella, presentados como
observatorio web con buscador de expedientes.

**Panel:** https://josehino.github.io/observatorio-contratacion-marbella/

**Se actualiza solo el día 25 de cada mes.**

---

## Fuente

**Una sola: los datos abiertos de la Plataforma de Contratación del Sector
Público.** No se usa ningún fichero local ni ningún listado enviado por correo:
todo lo que hay aquí se puede volver a descargar de la Plataforma, y por eso el
observatorio puede actualizarse solo.

| Dato | Fichero de sindicación | Enlace |
|---|---|---|
| Contratos **mayores** | `licitacionesPerfilesContratanteCompleto3` (`sindicacion_643`) | https://contrataciondelsectorpublico.gob.es/wps/portal/DatosAbiertos |
| Contratos **menores** | `contratosMenoresPerfilesContratantes` (`sindicacion_1143`) | https://contrataciondelsectorpublico.gob.es/wps/portal/DatosAbiertos |
| Ficha de cada expediente | — | https://contrataciondelestado.es/wps/portal/licitaciones |
| Especificación de los datos | Guía OpenPLACSP (PDF) | https://contrataciondelestado.es/datosabiertos/DGPE_PLACSP_OpenPLACSP_v.1.3.pdf |
| Códigos CODICE (tipos, procedimientos, CPV) | — | https://contrataciondelestado.es/codice/cl/ |

En el panel, **cada gráfica lleva debajo el enlace a su fuente** y cada
expediente del buscador enlaza a su ficha en la Plataforma.

### Hasta dónde llega cada serie

| | Desde | Motivo |
|---|---|---|
| Contratos mayores | 2018 | La LCSP 9/2017 obliga a publicar en el perfil desde marzo de 2018. |
| Contratos menores | **2022** | Antes de 2022 la Plataforma no recoge ningún contrato menor del Ayuntamiento. Ese hueco no se rellena con ninguna otra fuente. |

## Actualización automática

`.github/workflows/actualizar.yml` corre el **día 25 de cada mes a las 06:00 UTC**
(también a mano desde la pestaña Actions):

1. Descarga de la PLACSP **solo el ejercicio en curso**. Los años cerrados se
   reutilizan desde `_raw/cache/`, que sí está versionado —unos 22 MB—. Sin ese
   atajo habría que bajar 11 GB en cada pasada.
2. Extrae los expedientes de Marbella, reconstruye `observatorio/data/data.js`.
3. **Comprueba con Playwright que todas las gráficas pintan.** Si alguna sale
   vacía, la ejecución falla y no se publica nada.
4. Si la Plataforma no ha publicado nada nuevo, no toca el repositorio.

Para redescargar años concretos: Actions → *Actualizar observatorio* → *Run
workflow* → `anios: 2024,2025,2026`.

---

## Qué hay en este repositorio

| Ruta | Qué es |
|---|---|
| `observatorio/` | El panel. Chasis del kit en `assets/`, declaración en `app.js`, datos en `data/data.js`. |
| `index.html` | Redirección a `observatorio/` para GitHub Pages. |
| `csv/` | Un CSV por año y clase, más el consolidado `contratos_marbella_completo.csv`. Separador `;` y BOM: se abren en Excel con doble clic. |
| `contratos_marbella.json` | Todos los expedientes con su detalle, incluidas las adjudicaciones lote a lote. |
| `_raw/cache/` | El resultado de barrer cada ZIP anual. Versionado a propósito: es lo que hace barata la actualización mensual. |
| `_scripts/` | El pipeline. |

## El pipeline, en orden

```bash
python _scripts/download_placsp.py      # 1. ZIP anuales (reanudable; PLACSP_YEARS acota los años)
python _scripts/codigos.py              # 2. listas de códigos CODICE (tipos, CPV…)
python _scripts/extraer_marbella.py     # 3. filtra Marbella -> JSON + CSV
python _scripts/build_data.py           # 4. agrega -> observatorio/data/data.js
python _scripts/verificar.py            # 5. comprueba que TODAS las gráficas pintan
```

Los pasos 1 y 3 son incrementales: el descargador salta los ZIP ya presentes y
válidos, y el extractor cachea el resultado de cada ZIP. Un ZIP ausente cuya
caché existe se da por bueno, que es lo que permite correr el pipeline en un
runner sin los 11 GB.

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

## Limitaciones que hay que decir al cliente

- El observatorio refleja **lo publicado en la Plataforma**. Un expediente
  tramitado y no publicado no aparece.
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
