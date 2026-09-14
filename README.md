# Observatorio de Transparencia en la Contratación · Ayuntamiento de Marbella

Contratos **mayores, menores y modificados** del Ayuntamiento de Marbella,
presentados como observatorio web con buscador de expedientes.

**Panel:** https://josehino.github.io/observatorio-contratacion-marbella/

**Se actualiza solo el día 25 de cada mes.**

---

## Fuente

**Una sola: los documentos que el propio Ayuntamiento publica en la pestaña
«Documentos» de su perfil del contratante** en la Plataforma de Contratación
del Sector Público, que es donde el artículo 63 de la LCSP le obliga a
publicarlos.

https://contrataciondelestado.es/wps/portal/perfilContratante → buscar por NIF
`P2906900B` → *Junta de Gobierno del Ayuntamiento de Marbella* → **Documentos**

| Dato | Documento | Ejercicios |
|---|---|---|
| Contratos **mayores** | Listado Anual de Contratos celebrados · **indicador nº 48** | 2019 – 2024 |
| Contratos **menores** | Relaciones **trimestrales** de contratos menores (y listado anual donde no hay trimestrales) | 2018 – 2025 |
| **Modificados** | Relación de Modificados · **indicador nº 50** | 2019 – 2024 |

No se usa ningún fichero local, ningún Excel enviado por correo ni los ficheros
de datos abiertos de la Plataforma. Todo lo que hay aquí se puede volver a
descargar del perfil, y por eso el observatorio puede actualizarse solo.

La sección **«Documentos fuente»** del panel lista los 43 documentos que
alimentan cada cifra, con su enlace directo y cuántas filas aporta cada uno.
Los PDF originales están versionados en `_raw/perfil/`.

### Dos avisos que no se pueden omitir

**El IVA.** El listado de contratos mayores publica los importes **sin IVA** y
la relación de contratos menores, **con IVA**. Ninguno de los dos incluye la
otra base. Por eso el observatorio **no da ninguna cifra que sume mayores y
menores en euros**: sería falsa. Cada gráfica declara con qué base está. El
número de expedientes sí se suma, porque contar no depende del IVA.

**Las series terminan donde termina lo publicado.** Mayores en 2024 y menores
en 2025, que es el último listado que el Ayuntamiento ha subido. No hay 2026.

### Por qué mandan las relaciones trimestrales

Varios ejercicios tienen a la vez relaciones trimestrales y listado anual, y
**no dicen lo mismo**. La suma de los trimestres coincide con los totales que
el propio Ayuntamiento certifica; el listado anual trae a veces filas de más:

| Año | Suma de trimestres | Listado anual | Certificado por el Ayto. |
|---|---|---|---|
| 2021 | 693 | — | **693** |
| 2022 | 677 | 696 | **677** |
| 2023 | 616 (+19 del complementario) | 635 | **616** |
| 2025 | 621 | 621 | **621** |

Así que se usan las trimestrales, que además dan el trimestre. El listado anual
solo se usa en los ejercicios que no tienen trimestrales publicadas (2020).

## Actualización automática

`.github/workflows/actualizar.yml` corre el **día 25 de cada mes a las 06:00 UTC**
(también a mano desde la pestaña Actions):

1. Abre el perfil del contratante, lee la pestaña Documentos y descarga lo que
   aún no esté en `_raw/perfil/`. Lo ya descargado no se vuelve a pedir.
2. Extrae las tablas de los PDF nuevos y reconstruye `observatorio/data/data.js`.
3. **Comprueba con Playwright que todas las gráficas pintan**, en claro y en
   oscuro. Si alguna sale vacía, la ejecución falla y no se publica nada.
4. Si el Ayuntamiento no ha publicado nada nuevo, no toca el repositorio.

---

## Qué hay en este repositorio

| Ruta | Qué es |
|---|---|
| `observatorio/` | El panel. Chasis del kit en `assets/`, declaración en `app.js`, datos en `data/data.js`. |
| `index.html` | Redirección a `observatorio/` para GitHub Pages. |
| `_raw/perfil/` | Los PDF originales descargados del perfil, más `inventario.json` con título, fecha de publicación y URL de cada uno. |
| `listados_marbella.json` | Todas las filas extraídas, con el documento del que sale cada una. |
| `csv/` | Un CSV por clase. Separador `;` y BOM: se abren en Excel con doble clic. |
| `_scripts/` | El pipeline. |

## El pipeline, en orden

```bash
python _scripts/descargar_perfil.py     # 1. lee el perfil y descarga los PDF nuevos
python _scripts/extraer_listados.py     # 2. extrae las tablas -> listados_marbella.json + CSV
python _scripts/build_data.py           # 3. agrega -> observatorio/data/data.js
python _scripts/verificar.py            # 4. comprueba que TODAS las gráficas pintan
```

Requiere `pdfplumber` y `playwright`.

## Cómo se leen los PDF

Las cabeceras **no son iguales todos los años**: 2023 movió la columna «orden»
detrás del NIF, 2019 la llamaba «Nº Expediente Clave», 2020 partió
«A dministración» en dos y algún PDF rompe «Ejercici o» a mitad de palabra. Por
eso cada columna se localiza **por su nombre normalizado y sin espacios**, no
por su posición. Si una columna esperada no aparece, el documento se salta con
un aviso en vez de producir datos torcidos.

## Control de calidad

Los importes extraídos de los PDF, contrastados con los totales que el
Ayuntamiento certifica (que **no** se usan en el panel, solo como control):

| Año | Menores extraídos | Certificado | Desvío |
|---|---|---|---|
| 2021 | 5.121.497 € | 5.134.147 € | −0,25 % |
| 2022 | 4.339.821 € | 4.354.564 € | −0,34 % |
| 2024 | 3.970.894 € | 3.980.241 € | −0,23 % |
| 2025 | 4.687.510 € | 4.696.243 € | −0,19 % |

Los desvíos son las dos o tres filas que el PDF publica sin importe.

## Limitaciones que hay que decir al cliente

- El observatorio refleja **lo que el Ayuntamiento publica**. Un contrato
  tramitado y no incluido en estos listados no aparece.
- Los indicadores de competencia se calculan solo sobre los contratos en los
  que consta el número de licitadores. El panel publica esa cobertura.
- Los nombres de los adjudicatarios se reproducen **tal cual**: una misma
  empresa puede figurar con grafías distintas y contar dos veces. No se
  fusionan por parecido, porque eso sería inventar adjudicatarios.
- Los listados de mayores cuentan **lotes**, no solo expedientes: hay más filas
  que contratos.

---

Consultoría **AMMA Consulting** para el Ayuntamiento de Marbella · Marbella DTI.
