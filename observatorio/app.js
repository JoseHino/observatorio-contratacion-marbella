/* ============================================================================
   app.js — Observatorio de Transparencia en la Contratación de Marbella
   Declara las secciones; el kit (assets/) dibuja. Los datos los escribe
   _scripts/build_data.py a partir de dos fuentes:
     · contratos mayores  -> datos abiertos de la PLACSP
     · contratos menores  -> listados anuales del propio Ayuntamiento
   Todos los importes van en EUROS CON IVA, la única base común a ambas.
   ========================================================================== */
(function () {
  'use strict';

  var D = window.DATOS || {};
  var M = D.meta || {};
  var F = Obs.fmt;
  var esc = Obs.esc;

  var ANIOS = (D.resumen || {}).x || [];
  var ANIO_CURSO = M.anio_max;
  var iRef = ANIOS.indexOf(ANIO_CURSO - 1);      /* último ejercicio cerrado */

  /* Fuentes: SIEMPRE el enlace directo al sitio del que salen los datos. */
  var FUENTE_PLACSP = {
    txt: 'PLACSP · datos abiertos (licitacionesPerfilesContratanteCompleto3)',
    url: 'https://contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom'
  };
  var FUENTE_AYTO = {
    txt: 'Ayuntamiento de Marbella · Portal de Información Pública · Contratación pública',
    url: 'https://informacionpublica.marbella.es/ambitos/gestion-economica-y-administrativa/contratacion-publica.html'
  };
  var CHIP_ANUAL = { txt: 'Anual' };
  var CHIP_MAYORES = { txt: 'Contratos mayores', tipo: 'brand' };
  var CHIP_MENORES = { txt: 'Contratos menores', tipo: 'brand' };
  var NOTA_CURSO = ANIO_CURSO + ' es un ejercicio en curso: sus cifras no son comparables con las de un año completo.';
  var NOTA_CORTE = 'Aviso: el último contrato mayor del Ayuntamiento recogido en este fichero de la PLACSP es de ' + (M.ultimo_periodo || '') + '. Desde entonces el fichero no trae expedientes suyos, por lo que las barras de contratos mayores de los últimos años NO significan que el Ayuntamiento haya dejado de licitar: está pendiente comprobar si pasó a publicar a través de una plataforma agregada.';
  var NOTA_IVA = 'Importes con IVA. Es la única base común a las dos fuentes, porque el listado municipal de menores solo publica el importe con IVA.';

  function en(a, i) { return (a && a[i] != null && isFinite(a[i])) ? a[i] : null; }
  function delta(a, i) {
    var c = en(a, i), p = en(a, i - 1);
    return (c == null || p == null || !p) ? null : (c - p) / p * 100;
  }
  function eurM(v) { return v == null || !isFinite(v) ? '—' : F.num(v / 1e6, 1) + ' M€'; }
  function suma(a, b, i) { return (en(a, i) || 0) + (en(b, i) || 0) || null; }

  /* ------------------------------------------------------------- Secciones */

  var SECCIONES = [

    /* --------------------------------------------------------- Panorama --- */
    {
      id: 'panorama', nombre: 'Panorama',
      titulo: 'La contratación del Ayuntamiento en cifras',
      desc: 'El observatorio junta las dos mitades de la contratación municipal, que viven en sitios distintos: los <b>contratos mayores</b> salen de los datos abiertos de la Plataforma de Contratación del Sector Público, y los <b>contratos menores</b> de la relación anual que publica el propio Ayuntamiento, porque no los vuelca en la Plataforma. Se cuentan expedientes, no lotes.',
      render: function () {
        var r = D.resumen || {};
        return {
          hero: {
            valor: M.importe_total, label: 'Importe adjudicado acumulado ' + M.anio_min + '–' + M.anio_max + ' (con IVA)',
            formato: eurM,
            extra: [
              { label: 'Contratos mayores', valor: M.n_mayores, formato: F.num },
              { label: 'Contratos menores (desde ' + M.anio_min_menores + ')', valor: M.n_menores, formato: F.num },
              { label: 'Adjudicatarios distintos', valor: (D.empresas || {}).n_distintas, formato: F.num }
            ]
          },
          kpis: [
            { label: 'Expedientes en ' + (ANIO_CURSO - 1), valor: suma(r.n_mayores, r.n_menores, iRef),
              delta: delta(ANIOS.map(function (_, i) { return suma(r.n_mayores, r.n_menores, i); }), iRef),
              deltaRef: 'interanual',
              serie: ANIOS.map(function (_, i) { return suma(r.n_mayores, r.n_menores, i); }) },
            { label: 'Importe adjudicado en ' + (ANIO_CURSO - 1), formato: eurM,
              valor: suma(r.imp_mayores, r.imp_menores, iRef),
              delta: delta(ANIOS.map(function (_, i) { return suma(r.imp_mayores, r.imp_menores, i); }), iRef),
              deltaRef: 'interanual',
              serie: ANIOS.map(function (_, i) { return suma(r.imp_mayores, r.imp_menores, i); }) },
            { label: 'El menor, sobre el nº de expedientes', valor: en(r.pct_menores_num, iRef), unidad: '%', dec: 1,
              delta: delta(r.pct_menores_num, iRef), deltaRef: 'interanual', invertir: true, serie: r.pct_menores_num },
            { label: 'El menor, sobre el importe', valor: en(r.pct_menores_imp, iRef), unidad: '%', dec: 1,
              delta: delta(r.pct_menores_imp, iRef), deltaRef: 'interanual', invertir: true, serie: r.pct_menores_imp }
          ],
          cards: [
            {
              titulo: 'Expedientes por año', sub: 'Contratos mayores y menores',
              chips: [CHIP_ANUAL], fuente: FUENTE_PLACSP, ancho: 'full',
              nota: NOTA_CURSO + ' Los menores solo están disponibles desde ' + M.anio_min_menores + '. ' + NOTA_CORTE,
              spec: {
                type: 'stack', xType: 'anual', xLabel: 'Año', x: ANIOS, yFormat: 'num', xTodas: true,
                series: [
                  { name: 'Contratos mayores', data: (D.resumen || {}).n_mayores },
                  { name: 'Contratos menores', data: (D.resumen || {}).n_menores }
                ]
              }
            },
            {
              titulo: 'Importe adjudicado por año', sub: 'Euros con IVA',
              chips: [CHIP_ANUAL], fuente: FUENTE_PLACSP, ancho: 'full',
              nota: NOTA_IVA + ' ' + NOTA_CURSO + ' ' + NOTA_CORTE,
              spec: {
                type: 'stack', xType: 'anual', xLabel: 'Año', x: ANIOS, yFormat: 'eur', xTodas: true,
                series: [
                  { name: 'Contratos mayores', data: (D.resumen || {}).imp_mayores },
                  { name: 'Contratos menores', data: (D.resumen || {}).imp_menores }
                ]
              }
            },
            {
              titulo: 'Peso del contrato menor', sub: 'Porcentaje sobre el total del año',
              chips: [CHIP_ANUAL], fuente: FUENTE_PLACSP,
              nota: 'El contrato menor se adjudica sin licitación pública. Que sea mayoría en número es normal; lo que conviene vigilar es cuánto importe concentra.',
              spec: {
                type: 'line', xType: 'anual', xLabel: 'Año', x: ANIOS, yFormat: 'pct', desdeCero: true, xTodas: true,
                series: [
                  { name: 'Sobre el nº de expedientes', data: (D.resumen || {}).pct_menores_num },
                  { name: 'Sobre el importe', data: (D.resumen || {}).pct_menores_imp }
                ]
              }
            },
            {
              titulo: 'Presupuesto de licitación frente a adjudicación', sub: 'Solo contratos mayores · euros con IVA',
              chips: [CHIP_MAYORES], fuente: FUENTE_PLACSP,
              nota: 'La diferencia entre ambas barras es la baja de adjudicación. El contrato menor no aparece porque no tiene presupuesto de licitación publicado.',
              spec: {
                type: 'bar', xType: 'anual', xLabel: 'Año', x: ANIOS, yFormat: 'eur', xTodas: true,
                series: [
                  { name: 'Presupuesto de licitación', data: (D.resumen || {}).presupuesto },
                  { name: 'Importe adjudicado', data: (D.resumen || {}).adjudicado }
                ]
              }
            }
          ]
        };
      }
    },

    /* --------------------------------------------------- Contratos mayores */
    {
      id: 'mayores', nombre: 'Contratos mayores',
      titulo: 'Lo que se licita públicamente',
      desc: 'Los expedientes que el Ayuntamiento publica en su perfil del contratante de la Plataforma, con la codificación CODICE oficial. El procedimiento de adjudicación es el indicador de transparencia más directo: mide cuánta contratación se abre realmente a concurrencia.',
      render: function () {
        var t = D.tipos || {}, p = D.procedimientos || {}, e = D.estados || {};
        return {
          cards: [
            {
              titulo: 'Expedientes por tipo de contrato', sub: 'Serie anual',
              chips: [CHIP_MAYORES], fuente: FUENTE_PLACSP, ancho: 'full', nota: NOTA_CURSO,
              spec: {
                type: 'stack', xType: 'anual', xLabel: 'Año', x: t.x, yFormat: 'num', xTodas: true,
                series: (t.nombres || []).map(function (n, i) { return { name: n, data: t.n[i] }; })
              }
            },
            {
              titulo: 'Importe adjudicado por tipo de contrato', sub: 'Euros con IVA, serie anual',
              chips: [CHIP_MAYORES], fuente: FUENTE_PLACSP, ancho: 'full', nota: NOTA_CURSO,
              spec: {
                type: 'stack', xType: 'anual', xLabel: 'Año', x: t.x, yFormat: 'eur', xTodas: true,
                series: (t.nombres || []).map(function (n, i) { return { name: n, data: t.importe[i] }; })
              }
            },
            {
              titulo: 'Procedimiento de adjudicación', sub: 'Nº de expedientes del periodo',
              chips: [CHIP_MAYORES], fuente: FUENTE_PLACSP,
              spec: { type: 'barh', x: (p.x || []).slice().reverse(), yFormat: 'num', xLabel: 'Procedimiento',
                      series: [{ name: 'Expedientes', data: (p.n || []).slice().reverse() }] }
            },
            {
              titulo: 'Importe por procedimiento', sub: 'Euros con IVA, acumulado del periodo',
              chips: [CHIP_MAYORES], fuente: FUENTE_PLACSP,
              nota: 'El importe concentrado en procedimientos sin publicidad es la primera señal que mira una auditoría de contratación.',
              spec: { type: 'barh', x: (p.x || []).slice().reverse(), yFormat: 'eur', xLabel: 'Procedimiento',
                      series: [{ name: 'Importe adjudicado', data: (p.importe || []).slice().reverse() }] }
            },
            {
              titulo: 'Situación de los expedientes', sub: 'Estado en que figuran en la Plataforma',
              chips: [CHIP_MAYORES], fuente: FUENTE_PLACSP,
              spec: { type: 'donut', x: e.x, yFormat: 'num', series: [{ name: 'Expedientes', data: e.n }] }
            },
            {
              titulo: 'Procedimientos más usados, por año', sub: 'Nº de expedientes',
              chips: [CHIP_MAYORES], fuente: FUENTE_PLACSP, nota: NOTA_CURSO,
              spec: {
                type: 'stack', xType: 'anual', xLabel: 'Año', x: (p.por_anio || {}).x, yFormat: 'num', xTodas: true,
                series: ((p.por_anio || {}).nombres || []).map(function (n, i) { return { name: n, data: p.por_anio.n[i] }; })
              }
            }
          ]
        };
      }
    },

    /* --------------------------------------------------- Contratos menores */
    {
      id: 'menores', nombre: 'Contratos menores',
      titulo: 'Lo que se adjudica sin licitación',
      desc: 'El contrato menor —hasta 15.000 € en servicios y suministros y 40.000 € en obras— se adjudica directamente, sin concurrencia. El Ayuntamiento no lo vuelca en la Plataforma de Contratación: lo publica en su propia relación anual, y de ahí salen estas cifras. Los agregados usan los totales certificados por el Ayuntamiento; el listado contrato a contrato está en la pestaña de búsqueda.',
      render: function () {
        var m = D.menores || {}, r = D.resumen || {};
        var iM = ANIOS.indexOf(ANIO_CURSO - 1);
        return {
          nota: 'Los totales certificados existen para ' + (m.anios_certificados || []).join(', ') +
            '. El listado de detalle recoge ' + F.num(m.n_detalle) + ' contratos y no cuadra exactamente con ellos ' +
            '—procede de volcados en PDF con líneas partidas y repetidas—, así que las gráficas usan el total certificado y el buscador, el detalle.',
          kpis: [
            { label: 'Contratos menores en ' + (ANIO_CURSO - 1), valor: en(r.n_menores, iM),
              delta: delta(r.n_menores, iM), deltaRef: 'interanual', serie: r.n_menores },
            { label: 'Importe en ' + (ANIO_CURSO - 1), valor: en(r.imp_menores, iM), formato: eurM,
              delta: delta(r.imp_menores, iM), deltaRef: 'interanual', serie: r.imp_menores },
            { label: 'Importe medio por contrato', valor: (m.importe_medio || [])[(m.x || []).indexOf(ANIO_CURSO - 1)],
              formato: function (v) { return F.eur(v); } },
            { label: 'Proveedores distintos de menores', valor: (D.empresas || {}).n_solo_menores, formato: F.num }
          ],
          cards: [
            {
              titulo: 'Contratos menores por tipo', sub: 'Nº de contratos, serie anual',
              chips: [CHIP_MENORES], fuente: FUENTE_AYTO, ancho: 'full',
              spec: {
                type: 'stack', xType: 'anual', xLabel: 'Año', x: m.x, yFormat: 'num', xTodas: true,
                series: (m.nombres || []).map(function (n, i) { return { name: n, data: m.n[i] }; })
              }
            },
            {
              titulo: 'Importe de los contratos menores por tipo', sub: 'Euros con IVA, serie anual',
              chips: [CHIP_MENORES], fuente: FUENTE_AYTO, ancho: 'full',
              spec: {
                type: 'stack', xType: 'anual', xLabel: 'Año', x: m.x, yFormat: 'eur', xTodas: true,
                series: (m.nombres || []).map(function (n, i) { return { name: n, data: m.importe[i] }; })
              }
            },
            {
              titulo: 'Reparto por trimestre', sub: 'Importe adjudicado en cada trimestre, euros con IVA',
              chips: [CHIP_MENORES], fuente: FUENTE_AYTO, ancho: 'full',
              nota: 'La concentración en el cuarto trimestre es el patrón habitual del cierre presupuestario: conviene mirarla año a año.',
              spec: {
                type: 'bar', xType: 'cat', xLabel: 'Trimestre', x: (m.trimestres || {}).x, yFormat: 'eur', xTodas: true,
                series: ((m.trimestres || {}).anios || []).map(function (a, i) {
                  return { name: String(a), data: m.trimestres.importe[i] };
                })
              }
            },
            {
              titulo: 'Importe medio por contrato menor', sub: 'Euros con IVA',
              chips: [CHIP_MENORES], fuente: FUENTE_AYTO,
              spec: {
                type: 'bar', xType: 'anual', xLabel: 'Año', x: m.x, yFormat: 'eur', xTodas: true,
                series: [{ name: 'Importe medio', data: m.importe_medio }]
              }
            },
            {
              titulo: 'Mayores proveedores de contratos menores', sub: 'Euros con IVA, acumulado del periodo',
              chips: [CHIP_MENORES], fuente: FUENTE_AYTO, ancho: 'full', alto: 'tall',
              nota: 'Calculado sobre el listado de detalle, única fuente con el nombre del adjudicatario.',
              spec: { type: 'barh', x: ((D.empresas || {}).top_menores || {}).x, yFormat: 'eur', xLabel: 'Proveedor',
                      series: [{ name: 'Importe adjudicado', data: ((D.empresas || {}).top_menores || {}).v }] }
            }
          ]
        };
      }
    },

    /* --------------------------------------------------------- Materias --- */
    {
      id: 'materias', nombre: 'Materias',
      titulo: 'En qué se gasta',
      desc: 'Agrupación por la división del CPV —el vocabulario común de contratos públicos de la Unión Europea— del primer código declarado en cada expediente. Solo aplica a los contratos mayores: la relación municipal de menores no publica CPV.',
      render: function () {
        var c = D.cpv || {};
        return {
          cards: [
            {
              titulo: 'Importe adjudicado por materia', sub: 'Euros con IVA, acumulado del periodo',
              chips: [CHIP_MAYORES], fuente: FUENTE_PLACSP, ancho: 'full', alto: 'tall',
              spec: { type: 'barh', x: c.x, yFormat: 'eur', xLabel: 'Materia (división CPV)',
                      series: [{ name: 'Importe adjudicado', data: c.importe }] }
            },
            {
              titulo: 'Número de expedientes por materia', sub: 'Acumulado del periodo',
              chips: [CHIP_MAYORES], fuente: FUENTE_PLACSP, ancho: 'full', alto: 'tall',
              spec: { type: 'barh', x: c.x, yFormat: 'num', xLabel: 'Materia (división CPV)',
                      series: [{ name: 'Expedientes', data: c.n }] }
            }
          ]
        };
      }
    },

    /* --------------------------------------------------- Adjudicatarios --- */
    {
      id: 'empresas', nombre: 'Adjudicatarios',
      titulo: 'Quién contrata con el Ayuntamiento',
      desc: 'Empresas y profesionales adjudicatarios, sumando las dos fuentes. En los contratos mayores el importe se agrega por lote, de modo que una empresa que gana varios lotes de un expediente aparece con la suma de todos. Los nombres se toman tal cual vienen publicados: una misma empresa puede figurar con grafías distintas.',
      render: function () {
        var e = D.empresas || {};
        return {
          kpis: [
            { label: 'Adjudicatarios distintos', valor: e.n_distintas, formato: F.num },
            { label: 'Cuota de los 10 mayores', valor: e.concentracion, unidad: '%', dec: 1 },
            { label: 'Solo en contratos mayores', valor: e.n_solo_mayores, formato: F.num },
            { label: 'Solo en contratos menores', valor: e.n_solo_menores, formato: F.num }
          ],
          cards: [
            {
              titulo: 'Mayores adjudicatarios por importe', sub: 'Euros con IVA, mayores y menores, acumulado del periodo',
              chips: [CHIP_ANUAL], fuente: FUENTE_PLACSP, ancho: 'full', alto: 'tall',
              spec: { type: 'barh', x: (e.top_importe || {}).x, yFormat: 'eur', xLabel: 'Adjudicatario',
                      series: [{ name: 'Importe adjudicado', data: (e.top_importe || {}).v }] }
            },
            {
              titulo: 'Adjudicatarios más frecuentes', sub: 'Nº de adjudicaciones, acumulado del periodo',
              chips: [CHIP_ANUAL], fuente: FUENTE_PLACSP, ancho: 'full', alto: 'tall',
              nota: 'Ganar muchas veces no es por sí mismo un problema: en mantenimiento y suministros recurrentes es lo esperable. La señal a vigilar es que coincida con procedimientos sin concurrencia.',
              spec: { type: 'barh', x: (e.top_numero || {}).x, yFormat: 'num', xLabel: 'Adjudicatario',
                      series: [{ name: 'Adjudicaciones', data: (e.top_numero || {}).v }] }
            }
          ]
        };
      }
    },

    /* ------------------------------------------------------ Competencia --- */
    {
      id: 'competencia', nombre: 'Competencia',
      titulo: 'Cuánta concurrencia hay realmente',
      desc: 'Los indicadores que miden si la licitación municipal está abierta: cuántas empresas se presentan de media, con qué frecuencia se adjudica a la única oferta recibida y cuánto se rebaja el presupuesto al adjudicar. Solo se pueden calcular sobre contratos mayores, y únicamente sobre los expedientes en los que el órgano de contratación publicó el número de ofertas.',
      render: function () {
        var c = D.competencia || {};
        return {
          notaTipo: 'warn',
          nota: 'Estos indicadores dependen de que el órgano de contratación rellene los campos de resultado en la Plataforma. La última tarjeta muestra sobre cuántos expedientes se calcula cada año: con pocos, la media no es robusta.',
          kpis: [
            { label: 'Ofertas por licitación en ' + (ANIO_CURSO - 1), valor: en(c.media_ofertas, iRef), dec: 1,
              delta: delta(c.media_ofertas, iRef), deltaRef: 'interanual', serie: c.media_ofertas },
            { label: 'Adjudicaciones con una sola oferta', valor: en(c.pct_una_oferta, iRef), unidad: '%', dec: 1,
              delta: delta(c.pct_una_oferta, iRef), deltaRef: 'interanual', invertir: true, serie: c.pct_una_oferta },
            { label: 'Baja media de adjudicación en ' + (ANIO_CURSO - 1), valor: en(c.baja_media, iRef), unidad: '%', dec: 1,
              delta: delta(c.baja_media, iRef), deltaRef: 'interanual', serie: c.baja_media }
          ],
          cards: [
            {
              titulo: 'Ofertas recibidas por licitación', sub: 'Media anual',
              chips: [CHIP_MAYORES], fuente: FUENTE_PLACSP, ancho: 'full',
              spec: {
                type: 'line', xType: 'anual', xLabel: 'Año', x: c.x, yFormat: 'dec1', desdeCero: true, xTodas: true,
                series: [{ name: 'Ofertas por licitación', data: c.media_ofertas }],
                ref: 3, refLabel: 'Referencia: 3 ofertas'
              }
            },
            {
              titulo: 'Adjudicaciones con una sola oferta', sub: 'Porcentaje de las licitaciones con nº de ofertas publicado',
              chips: [CHIP_MAYORES], fuente: FUENTE_PLACSP,
              nota: 'Adjudicar a la única empresa que se presenta es legal, pero repetido en el tiempo indica que el mercado no está llegando a la licitación.',
              spec: {
                type: 'bar', xType: 'anual', xLabel: 'Año', x: c.x, yFormat: 'pct', xTodas: true,
                series: [{ name: 'Una sola oferta', data: c.pct_una_oferta }]
              }
            },
            {
              titulo: 'Baja media de adjudicación', sub: 'Rebaja sobre el presupuesto de licitación, sin IVA',
              chips: [CHIP_MAYORES], fuente: FUENTE_PLACSP,
              nota: 'Se agregan presupuesto e importe adjudicado de los expedientes que publican ambos —en euros sin IVA, que es donde son comparables— en lugar de promediar porcentajes: así los contratos grandes pesan lo que les corresponde.',
              spec: {
                type: 'bar', xType: 'anual', xLabel: 'Año', x: c.x, yFormat: 'pct', xTodas: true,
                series: [{ name: 'Baja media', data: c.baja_media }]
              }
            },
            {
              titulo: 'Expedientes sobre los que se calcula', sub: 'Licitaciones con número de ofertas publicado',
              chips: [CHIP_MAYORES], fuente: FUENTE_PLACSP,
              nota: 'Es la cobertura del indicador, no un dato de contratación: cuanto más baja, menos representativas son las tres tarjetas anteriores.',
              spec: {
                type: 'bar', xType: 'anual', xLabel: 'Año', x: c.x, yFormat: 'num', xTodas: true,
                series: [{ name: 'Expedientes informados', data: c.n_informados }]
              }
            }
          ]
        };
      }
    },

    /* --------------------------------------------------------- Buscador --- */
    {
      id: 'buscador', nombre: 'Buscar contrato',
      titulo: 'Buscador de expedientes',
      desc: 'Los contratos uno a uno, mayores y menores juntos. Busca por objeto, número de expediente, adjudicatario, NIF u órgano; los filtros se combinan entre sí. Los contratos mayores enlazan con su ficha oficial en la Plataforma.',
      render: function () { return { extra: Buscador.html() }; }
    }
  ];

  /* ========================================================================
     Buscador — bloque libre de sección (res.extra). Todo se engancha con
     addEventListener delegado en la raíz, nunca con onclick en el marcado.
     ====================================================================== */

  var Buscador = (function () {
    var B = D.busqueda || { campos: [], filas: [], claves: [] };
    var IX = {};
    (B.campos || []).forEach(function (c, i) { IX[c] = i; });

    var PAGINA = 40;
    var vacio = { q: '', anio: '', clase: '', tipo: '', proc: '', orden: 'anio', n: PAGINA };
    var st = Object.keys(vacio).reduce(function (o, k) { o[k] = vacio[k]; return o; }, {});
    var resultado = B.filas.slice();

    function norm(s) {
      return String(s == null ? '' : s).normalize('NFKD')
        .replace(/[\u0300-\u036f]/g, '').toLowerCase();
    }

    function unicos(campo) {
      var v = {};
      B.filas.forEach(function (f) { var x = f[IX[campo]]; if (x) v[x] = (v[x] || 0) + 1; });
      return Object.keys(v).sort(function (a, b) { return v[b] - v[a]; });
    }

    function opciones(lista, sel) {
      return lista.map(function (o) {
        return '<option value="' + esc(o) + '"' + (String(o) === String(sel) ? ' selected' : '') + '>' + esc(o) + '</option>';
      }).join('');
    }

    function filtrar() {
      var terminos = norm(st.q).split(/\s+/).filter(Boolean);
      resultado = B.filas.filter(function (f, i) {
        if (st.anio && String(f[IX.a]) !== st.anio) return false;
        if (st.clase && f[IX.f] !== st.clase) return false;
        if (st.tipo && f[IX.ti] !== st.tipo) return false;
        if (st.proc && f[IX.pr] !== st.proc) return false;
        if (!terminos.length) return true;
        var k = B.claves[i];
        for (var t = 0; t < terminos.length; t++) if (k.indexOf(terminos[t]) < 0) return false;
        return true;
      });
      var imp = function (f) { return f[IX.imp] || f[IX.pre] || 0; };
      if (st.orden === 'importe') resultado.sort(function (a, b) { return imp(b) - imp(a); });
      else if (st.orden === 'importe_asc') resultado.sort(function (a, b) { return imp(a) - imp(b); });
      else resultado.sort(function (a, b) {
        return (b[IX.fa] || String(b[IX.a])).localeCompare(a[IX.fa] || String(a[IX.a]));
      });
      st.n = PAGINA;
    }

    function clase(f) { return f[IX.f] === 'M' ? 'Menor' : 'Mayor'; }

    function filaHtml(f, i) {
      var imp = f[IX.imp], pre = f[IX.pre];
      return '<tr class="bs-row" data-fila="' + i + '">' +
        '<td class="bs-anio">' + esc(f[IX.a]) + '</td>' +
        '<td><span class="obs-chip' + (f[IX.f] === 'M' ? '' : ' brand') + '">' + clase(f) + '</span></td>' +
        '<td class="bs-exp">' + esc(f[IX.ex] || '—') + '</td>' +
        '<td class="bs-obj">' + esc(f[IX.ob] || '—') + '</td>' +
        '<td>' + esc(f[IX.adj] || '—') + '</td>' +
        '<td class="bs-num">' + (imp != null ? F.eur(imp)
          : (pre != null ? '<span class="bs-mut">' + F.eur(pre) + '</span>' : '—')) + '</td>' +
        '</tr>' +
        '<tr class="bs-det" data-det="' + i + '" hidden><td colspan="6">' + detalleHtml(f) + '</td></tr>';
    }

    function dato(l, v) {
      return v ? '<div><dt>' + esc(l) + '</dt><dd>' + esc(v) + '</dd></div>' : '';
    }

    function detalleHtml(f) {
      var enlace = f[IX.url]
        ? '<a class="obs-btn" href="' + esc(f[IX.url]) + '" target="_blank" rel="noopener">Ficha en la Plataforma ' + Obs.icono.externo() + '</a>'
        : '<span class="bs-mut">Los contratos menores no tienen ficha en la Plataforma: proceden de la relación anual publicada por el Ayuntamiento.</span>';
      return '<div class="bs-detalle"><dl>' +
        dato('Expediente', f[IX.ex]) +
        dato('Órgano de contratación', f[IX.or]) +
        dato('Tipo de contrato', f[IX.ti]) +
        dato('Procedimiento', f[IX.pr]) +
        dato('Estado', f[IX.es]) +
        dato('Materia (CPV)', f[IX.cp]) +
        dato('Adjudicatario', f[IX.adj]) +
        dato('NIF del adjudicatario', f[IX.nif]) +
        dato('Presupuesto de licitación (con IVA)', f[IX.pre] != null ? F.eur(f[IX.pre]) : '') +
        dato('Importe adjudicado (con IVA)', f[IX.imp] != null ? F.eur(f[IX.imp]) : '') +
        dato('Fecha de adjudicación', f[IX.fa]) +
        '</dl><p class="bs-objeto">' + esc(f[IX.ob]) + '</p>' + enlace + '</div>';
    }

    function resumenHtml() {
      var imp = resultado.reduce(function (s, f) { return s + (f[IX.imp] || f[IX.pre] || 0); }, 0);
      return '<b>' + F.num(resultado.length) + '</b> contrato' + (resultado.length === 1 ? '' : 's') +
        ' · <b>' + F.eur(imp) + '</b> con IVA' +
        (resultado.length ? ' · mostrando ' + F.num(Math.min(st.n, resultado.length)) : '');
    }

    function listaHtml() {
      if (!resultado.length) {
        return '<div class="obs-msg">No hay ningún contrato que cumpla estos criterios. Prueba con menos filtros o con otra palabra del objeto.</div>';
      }
      return '<div class="bs-tabla-wrap"><table class="obs-table bs-tabla">' +
        '<colgroup><col class="c-anio"><col class="c-clase"><col class="c-exp">' +
        '<col><col class="c-adj"><col class="c-imp"></colgroup>' +
        '<thead><tr>' +
        '<th>Año</th><th>Clase</th><th>Expediente</th><th>Objeto</th><th>Adjudicatario</th><th class="bs-num">Importe</th>' +
        '</tr></thead><tbody>' +
        resultado.slice(0, st.n).map(function (f) { return filaHtml(f, B.filas.indexOf(f)); }).join('') +
        '</tbody></table></div>' +
        (resultado.length > st.n
          ? '<div class="bs-mas"><button type="button" class="obs-btn" data-bs="mas">Mostrar ' +
            F.num(Math.min(PAGINA * 4, resultado.length - st.n)) + ' más</button></div>'
          : '');
    }

    function html() {
      filtrar();
      return '<div class="bs" id="bs">' +
        '<div class="bs-filtros">' +
          '<label class="bs-buscar"><span class="obs-sr">Buscar</span>' +
            '<input type="search" id="bs-q" class="obs-select" value="' + esc(st.q) + '" ' +
            'placeholder="Objeto, expediente, adjudicatario o NIF…" autocomplete="off"></label>' +
          '<label class="obs-card-ctrl"><span>Año</span><select class="obs-select" data-bs="anio">' +
            '<option value="">Todos</option>' + opciones(unicos('a').sort().reverse(), st.anio) + '</select></label>' +
          '<label class="obs-card-ctrl"><span>Clase</span><select class="obs-select" data-bs="clase">' +
            '<option value="">Todas</option>' +
            '<option value="m"' + (st.clase === 'm' ? ' selected' : '') + '>Contratos mayores</option>' +
            '<option value="M"' + (st.clase === 'M' ? ' selected' : '') + '>Contratos menores</option></select></label>' +
          '<label class="obs-card-ctrl"><span>Tipo</span><select class="obs-select" data-bs="tipo">' +
            '<option value="">Todos</option>' + opciones(unicos('ti'), st.tipo) + '</select></label>' +
          '<label class="obs-card-ctrl"><span>Procedimiento</span><select class="obs-select" data-bs="proc">' +
            '<option value="">Todos</option>' + opciones(unicos('pr'), st.proc) + '</select></label>' +
          '<label class="obs-card-ctrl"><span>Orden</span><select class="obs-select" data-bs="orden">' +
            '<option value="anio">Más recientes</option>' +
            '<option value="importe"' + (st.orden === 'importe' ? ' selected' : '') + '>Mayor importe</option>' +
            '<option value="importe_asc"' + (st.orden === 'importe_asc' ? ' selected' : '') + '>Menor importe</option>' +
            '</select></label>' +
          '<button type="button" class="obs-btn" data-bs="csv">' + Obs.icono.csv() + 'Descargar resultados</button>' +
          '<button type="button" class="obs-btn" data-bs="limpiar">Limpiar</button>' +
        '</div>' +
        '<div class="bs-resumen" id="bs-resumen">' + resumenHtml() + '</div>' +
        '<div id="bs-lista">' + listaHtml() + '</div>' +
      '</div>';
    }

    function repintar() {
      var lista = document.getElementById('bs-lista');
      var res = document.getElementById('bs-resumen');
      if (lista) lista.innerHTML = listaHtml();
      if (res) res.innerHTML = resumenHtml();
    }

    function csv() {
      var cab = ['Año', 'Clase', 'Expediente', 'Objeto', 'Órgano', 'Tipo', 'Procedimiento', 'Estado',
                 'Materia CPV', 'Adjudicatario', 'NIF', 'Presupuesto con IVA', 'Importe adjudicado con IVA',
                 'Fecha adjudicación', 'Enlace'];
      var lim = function (v) { return '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"'; };
      var num = function (v) { return v == null ? '' : String(v).replace('.', ','); };
      var lin = [cab.join(';')];
      resultado.forEach(function (f) {
        lin.push([lim(f[IX.a]), lim(clase(f)), lim(f[IX.ex]), lim(f[IX.ob]), lim(f[IX.or]), lim(f[IX.ti]),
                  lim(f[IX.pr]), lim(f[IX.es]), lim(f[IX.cp]), lim(f[IX.adj]), lim(f[IX.nif]),
                  num(f[IX.pre]), num(f[IX.imp]), lim(f[IX.fa]), lim(f[IX.url])].join(';'));
      });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob(['﻿' + lin.join('\r\n')], { type: 'text/csv;charset=utf-8' }));
      a.download = 'contratos_marbella_seleccion.csv';
      document.body.appendChild(a); a.click(); a.remove();
    }

    /* Un único listener delegado en la raíz: sirve también para el marcado que
       todavía no existe cuando se engancha (las secciones se pintan al abrirlas). */
    function enganchar(raiz) {
      var t = null;
      raiz.addEventListener('input', function (ev) {
        if (ev.target.id !== 'bs-q') return;
        clearTimeout(t);
        var v = ev.target.value;
        t = setTimeout(function () { st.q = v; filtrar(); repintar(); }, 180);
      });
      raiz.addEventListener('change', function (ev) {
        var s = ev.target.closest ? ev.target.closest('select[data-bs]') : null;
        if (!s) return;
        st[s.getAttribute('data-bs')] = s.value;
        filtrar(); repintar();
      });
      raiz.addEventListener('click', function (ev) {
        var b = ev.target.closest('button[data-bs]');
        if (b) {
          var acc = b.getAttribute('data-bs');
          if (acc === 'mas') { st.n += PAGINA * 4; repintar(); return; }
          if (acc === 'csv') { csv(); return; }
          if (acc === 'limpiar') {
            Object.keys(vacio).forEach(function (k) { st[k] = vacio[k]; });
            Obs.refrescar('buscador');
            return;
          }
        }
        var fila = ev.target.closest('.bs-row');
        if (fila && !ev.target.closest('a')) {
          var det = document.querySelector('.bs-det[data-det="' + fila.getAttribute('data-fila') + '"]');
          if (det) { det.hidden = !det.hidden; fila.classList.toggle('abierta', !det.hidden); }
        }
      });
    }

    return { html: html, enganchar: enganchar };
  })();

  /* ----------------------------------------------------------- Arranque -- */

  Obs.init({
    titulo: 'Observatorio de Transparencia en la Contratación',
    subtitulo: 'Ayuntamiento de Marbella · ' + M.anio_min + '–' + M.anio_max + ' · contratos mayores y menores',
    secciones: SECCIONES,
    actualizado: M.actualizado,
    fuentes: [
      FUENTE_PLACSP,
      FUENTE_AYTO,
      { txt: 'PLACSP · portal de datos abiertos (todos los ficheros de sindicación)',
        url: 'https://contrataciondelsectorpublico.gob.es/wps/portal/DatosAbiertos' },
      { txt: 'PLACSP · buscador de licitaciones (ficha de cada expediente)',
        url: 'https://contrataciondelestado.es/wps/portal/licitaciones' },
      { txt: 'Perfil del contratante del Ayuntamiento de Marbella',
        url: 'https://ayuntamiento.marbella.es/oferta-publica/perfil-del-contratante.html' },
      { txt: 'Guía oficial de los datos abiertos de la PLACSP (PDF)',
        url: 'https://contrataciondelestado.es/datosabiertos/DGPE_PLACSP_OpenPLACSP_v.1.3.pdf' },
      { txt: 'Códigos CODICE (tipos de contrato, procedimientos, CPV)',
        url: 'https://contrataciondelestado.es/codice/cl/' }
    ],
    metodologia:
      '<b>Contratos mayores.</b> Ficheros de sindicación de la PLACSP ' +
      '(<a href="https://contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom" ' +
      'target="_blank" rel="noopener"><code>licitacionesPerfilesContratanteCompleto3</code></a>). Un proceso automático descarga los ficheros ' +
      'anuales completos, selecciona los expedientes cuyo <i>órgano de contratación</i> —nunca el objeto— es el ' +
      'Ayuntamiento de Marbella (NIF ' + esc(M.nif) + ', DIR3 L01290691) o un ente municipal dependiente, conserva ' +
      'la versión más reciente de cada expediente y traduce los códigos CODICE a su descripción oficial. ' +
      '<br><br><b>Contratos menores.</b> El Ayuntamiento no los publica en la PLACSP —comprobado fichero a fichero ' +
      'en los datos abiertos—, así que proceden de la ' +
      '<a href="https://informacionpublica.marbella.es/ambitos/gestion-economica-y-administrativa/contratacion-publica.html" ' +
      'target="_blank" rel="noopener">relación anual que publica el propio Ayuntamiento</a>. Las gráficas usan los totales ' +
      'certificados por el Ayuntamiento y el buscador, el listado de detalle. ' +
      '<br><br>Todos los importes van <b>con IVA</b>, la única base común a las dos fuentes. Cada tarjeta permite ' +
      'ver los datos en tabla y descargarlos en CSV; el buscador exporta la selección completa.',
    pie: '<b>El fichero de datos abiertos de la PLACSP deja de traer contratos mayores del Ayuntamiento después de ' +
      esc(M.ultimo_periodo || '') + '.</b> No es un cero de contratación: lo más probable es que el Ayuntamiento pasara a '+
      'publicar por una plataforma agregada, pendiente de comprobar. Las cifras de contratos mayores de los últimos ' +
      'años deben leerse con esa reserva. <br><br>' +
      'El observatorio refleja lo publicado: un expediente tramitado y no publicado no aparece, y los campos ' +
      'que el órgano de contratación deja vacíos —número de ofertas, importe de adjudicación— quedan fuera de los ' +
      'indicadores que dependen de ellos. La Plataforma ofusca el NIF de las personas físicas. ' +
      'Las cifras de ' + M.anio_max + ' corresponden a un ejercicio en curso.'
  });

  Buscador.enganchar(document.getElementById('obs-app'));

  Obs.estado('Última publicación recogida: ' + (M.ultimo_periodo || '—') +
    ' · ' + F.num(M.n_mayores) + ' mayores y ' + F.num(M.n_menores) + ' menores', 'live');

})();
