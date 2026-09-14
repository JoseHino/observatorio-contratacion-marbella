/* ============================================================================
   app.js — Observatorio de Transparencia en la Contratación de Marbella
   Declara las secciones; el kit (assets/) dibuja. Los datos los escribe
   _scripts/build_data.py desde los documentos que el propio Ayuntamiento
   publica en su perfil del contratante de la PLACSP (artículo 63 LCSP).

   REGLA QUE NO SE ROMPE: los listados de contratos mayores publican el
   importe SIN IVA y los de menores CON IVA, y ninguno trae la otra base.
   Aquí no se suman euros de mayores y menores en ninguna tarjeta. Lo que sí
   se suma es el número de expedientes.
   ========================================================================== */
(function () {
  'use strict';

  var D = window.DATOS || {};
  var M = D.meta || {};
  var F = Obs.fmt;
  var esc = Obs.esc;

  var FUENTE = {
    txt: 'Perfil del contratante del Ayuntamiento de Marbella · Documentos',
    url: 'https://contrataciondelestado.es/wps/portal/perfilContratante'
  };
  var CHIP_MAY = { txt: 'Contratos mayores', tipo: 'brand' };
  var CHIP_MEN = { txt: 'Contratos menores', tipo: 'brand' };
  var CHIP_MOD = { txt: 'Modificados', tipo: 'brand' };
  var SIN_IVA = 'Importes SIN IVA: es como los publica el listado anual de contratos.';
  var CON_IVA = 'Importes CON IVA: es como los publica la relación de contratos menores.';
  var NOTA_TIPOS = 'Los listados escriben el tipo de contrato en singular y en plural indistintamente ' +
    '—«Servicio» y «Servicios», «Obra» y «Obras»— y con alguna errata de volcado. Aquí se unifican: es un ' +
    'vocabulario cerrado de la Ley de Contratos, no una fusión por parecido. Sin unificarlo, Obras no llegaba ' +
    'a aparecer en las gráficas de contratos menores.';

  function en(a, i) { return (a && i >= 0 && a[i] != null && isFinite(a[i])) ? a[i] : null; }
  function delta(a, i) {
    var c = en(a, i), p = en(a, i - 1);
    return (c == null || p == null || !p) ? null : (c - p) / p * 100;
  }
  function eurM(v) { return v == null || !isFinite(v) ? '—' : F.num(v / 1e6, 1) + ' M€'; }
  function ult(a) { return a && a.length ? a.length - 1 : -1; }
  function idx(a, v) { return (a || []).indexOf(v); }

  function series(nombres, datos) {
    return (nombres || []).map(function (n, i) { return { name: n, data: (datos || [])[i] }; });
  }

  /* ---------------------------------------------------------- Buscador --- */

  var Buscador = (function () {
    var B = D.busqueda || { campos: [], filas: [], claves: [] };
    var IX = {};
    (B.campos || []).forEach(function (c, i) { IX[c] = i; });

    var PAGINA = 40;
    var vacio = { q: '', anio: '', clase: '', tipo: '', proc: '', orden: 'anio', n: PAGINA };
    var st = Object.keys(vacio).reduce(function (o, k) { o[k] = vacio[k]; return o; }, {});
    var resultado = B.filas.slice();

    var CLASES = { m: 'Mayor', M: 'Menor', x: 'Modificado' };

    function norm(s) {
      return String(s == null ? '' : s).normalize('NFKD')
        .replace(/[̀-ͯ]/g, '').toLowerCase();
    }

    function unicos(campo) {
      var v = {};
      B.filas.forEach(function (f) { var x = f[IX[campo]]; if (x) v[x] = (v[x] || 0) + 1; });
      return Object.keys(v).sort(function (a, b) { return v[b] - v[a]; });
    }

    function opciones(lista, sel) {
      return lista.map(function (o) {
        return '<option value="' + esc(o) + '"' + (String(o) === String(sel) ? ' selected' : '') +
          '>' + esc(o) + '</option>';
      }).join('');
    }

    function filtrar() {
      var terminos = norm(st.q).split(/\s+/).filter(Boolean);
      resultado = B.filas.filter(function (f, i) {
        if (st.anio && String(f[IX.a]) !== st.anio) return false;
        if (st.clase && f[IX.cl] !== st.clase) return false;
        if (st.tipo && f[IX.ti] !== st.tipo) return false;
        if (st.proc && f[IX.pr] !== st.proc) return false;
        if (!terminos.length) return true;
        var k = B.claves[i];
        for (var t = 0; t < terminos.length; t++) if (k.indexOf(terminos[t]) < 0) return false;
        return true;
      });
      var imp = function (f) { return f[IX.imp] || 0; };
      if (st.orden === 'importe') resultado.sort(function (a, b) { return imp(b) - imp(a); });
      else if (st.orden === 'importe_asc') resultado.sort(function (a, b) { return imp(a) - imp(b); });
      else resultado.sort(function (a, b) {
        return (b[IX.f] || String(b[IX.a])).localeCompare(a[IX.f] || String(a[IX.a]));
      });
      st.n = PAGINA;
    }

    function dato(l, v) {
      return v ? '<div><dt>' + esc(l) + '</dt><dd>' + esc(v) + '</dd></div>' : '';
    }

    function detalleHtml(f) {
      var cl = f[IX.cl];
      var base = cl === 'M' ? 'con IVA' : 'sin IVA';
      var etiqueta = cl === 'x' ? 'Importe de la modificación' : 'Importe adjudicado';
      var enlace = f[IX.url]
        ? '<a class="obs-btn" href="' + esc(f[IX.url]) + '" target="_blank" rel="noopener">' +
          'Abrir el documento del que sale ' + Obs.icono.externo() + '</a>'
        : '';
      return '<div class="bs-detalle"><dl>' +
        dato('Expediente', f[IX.ex]) +
        dato('Clase', CLASES[cl]) +
        dato('Tipo de contrato', f[IX.ti]) +
        dato('Procedimiento', f[IX.pr]) +
        dato('Adjudicatario', f[IX.adj]) +
        dato('NIF del adjudicatario', f[IX.nif]) +
        dato('Presupuesto de licitación (sin IVA)', f[IX.lic] != null ? F.eur(f[IX.lic]) : '') +
        dato(etiqueta + ' (' + base + ')', f[IX.imp] != null ? F.eur(f[IX.imp]) : '') +
        dato('Fecha de formalización', f[IX.f]) +
        dato('Documento publicado', f[IX.doc]) +
        '</dl><p class="bs-objeto">' + esc(f[IX.ob]) + '</p>' + enlace + '</div>';
    }

    function filaHtml(f, i) {
      var imp = f[IX.imp], cl = f[IX.cl];
      return '<tr class="bs-row" data-fila="' + i + '">' +
        '<td class="bs-anio">' + esc(f[IX.a]) + '</td>' +
        '<td><span class="obs-chip' + (cl === 'm' ? ' brand' : '') + '">' + esc(CLASES[cl] || cl) + '</span></td>' +
        '<td class="bs-exp">' + esc(f[IX.ex] || '—') + '</td>' +
        '<td class="bs-obj">' + esc(f[IX.ob] || '—') + '</td>' +
        '<td>' + esc(f[IX.adj] || '—') + '</td>' +
        '<td class="bs-num">' + (imp != null ? F.eur(imp) : '—') + '</td>' +
        '</tr>' +
        '<tr class="bs-det" data-det="' + i + '" hidden><td colspan="6">' + detalleHtml(f) + '</td></tr>';
    }

    function resumenHtml() {
      var may = 0, men = 0, mod = 0;
      resultado.forEach(function (f) {
        var v = f[IX.imp] || 0;
        if (f[IX.cl] === 'm') may += v; else if (f[IX.cl] === 'M') men += v; else mod += v;
      });
      var trozos = [];
      if (may) trozos.push('<b>' + F.eur(may) + '</b> en mayores (sin IVA)');
      if (men) trozos.push('<b>' + F.eur(men) + '</b> en menores (con IVA)');
      if (mod) trozos.push('<b>' + F.eur(mod) + '</b> en modificados (sin IVA)');
      return '<b>' + F.num(resultado.length) + '</b> registro' + (resultado.length === 1 ? '' : 's') +
        (trozos.length ? ' · ' + trozos.join(' · ') : '') +
        (resultado.length ? ' · mostrando ' + F.num(Math.min(st.n, resultado.length)) : '');
    }

    function listaHtml() {
      if (!resultado.length) {
        return '<div class="obs-msg">No hay ningún contrato que cumpla estos criterios. ' +
          'Prueba con menos filtros o con otra palabra del objeto.</div>';
      }
      return '<div class="bs-tabla-wrap"><table class="obs-table bs-tabla">' +
        '<colgroup><col class="c-anio"><col class="c-clase"><col class="c-exp">' +
        '<col><col class="c-adj"><col class="c-imp"></colgroup>' +
        '<thead><tr>' +
        '<th>Año</th><th>Clase</th><th>Expediente</th><th>Objeto</th>' +
        '<th>Adjudicatario</th><th class="bs-num">Importe</th>' +
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
            '<option value="M"' + (st.clase === 'M' ? ' selected' : '') + '>Contratos menores</option>' +
            '<option value="x"' + (st.clase === 'x' ? ' selected' : '') + '>Modificados</option></select></label>' +
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
      var cab = ['Año', 'Clase', 'Expediente', 'Objeto', 'Tipo', 'Procedimiento', 'Adjudicatario', 'NIF',
                 'Importe', 'Base IVA', 'Presupuesto licitación sin IVA', 'Fecha formalización',
                 'Documento', 'Enlace'];
      var lim = function (v) { return '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"'; };
      var num = function (v) { return v == null ? '' : String(v).replace('.', ','); };
      var lin = [cab.join(';')];
      resultado.forEach(function (f) {
        var cl = f[IX.cl];
        lin.push([lim(f[IX.a]), lim(CLASES[cl]), lim(f[IX.ex]), lim(f[IX.ob]), lim(f[IX.ti]),
                  lim(f[IX.pr]), lim(f[IX.adj]), lim(f[IX.nif]), num(f[IX.imp]),
                  lim(cl === 'M' ? 'con IVA' : 'sin IVA'), num(f[IX.lic]), lim(f[IX.f]),
                  lim(f[IX.doc]), lim(f[IX.url])].join(';'));
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

  /* ---------------------------------------------------------- Secciones -- */

  var SECCIONES = [

    /* --------------------------------------------------------- Panorama --- */
    {
      id: 'panorama', nombre: 'Panorama',
      titulo: 'La contratación del Ayuntamiento en cifras',
      desc: 'Todo lo que hay aquí sale de los documentos que el propio Ayuntamiento publica en su perfil del contratante, como le obliga el artículo 63 de la Ley de Contratos: el <b>listado anual de contratos</b> (indicador nº 48) y las <b>relaciones trimestrales de contratos menores</b>. No se usa ninguna otra fuente.',
      render: function () {
        var r = D.resumen || {}, x = r.x || [];
        return {
          nota: 'Las dos mitades no se pueden sumar en euros. El listado de contratos mayores publica los importes <b>sin IVA</b> y la relación de menores, <b>con IVA</b>, y ninguno de los dos incluye la otra base. Por eso no verás aquí ninguna cifra global de «lo que contrata el Ayuntamiento»: sería falsa. El número de expedientes sí se suma.',
          kpis: [
            { label: 'Contratos mayores ' + M.anio_min_may + '–' + M.anio_max_may, valor: M.n_mayores, formato: F.num },
            { label: 'Contratos menores ' + M.anio_min_men + '–' + M.anio_max_men, valor: M.n_menores, formato: F.num },
            { label: 'Adjudicado en mayores (sin IVA)', valor: M.imp_mayores, formato: eurM },
            { label: 'Adjudicado en menores (con IVA)', valor: M.imp_menores, formato: eurM }
          ],
          cards: [
            {
              titulo: 'Expedientes por año', sub: 'Número de contratos, mayores y menores',
              chips: [{ txt: 'Anual' }], fuente: FUENTE, ancho: 'full',
              nota: 'El número sí es comparable entre las dos clases. Los mayores llegan hasta ' + M.anio_max_may +
                ' y los menores hasta ' + M.anio_max_men + ', que es hasta donde el Ayuntamiento ha publicado cada listado.',
              spec: {
                type: 'stack', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'num', xTodas: true,
                series: [
                  { name: 'Contratos mayores', data: r.n_mayores },
                  { name: 'Contratos menores', data: r.n_menores }
                ]
              }
            },
            {
              titulo: 'Peso del contrato menor', sub: 'Porcentaje sobre el número de expedientes del año',
              chips: [{ txt: 'Anual' }], fuente: FUENTE,
              nota: 'El contrato menor se adjudica a dedo, sin concurrencia. Que sean mayoría en número es lo normal; lo que conviene vigilar es cuánto importe concentran.',
              spec: {
                type: 'line', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'pct', xTodas: true,
                series: [{ name: 'Menores sobre el total', data: r.pct_menores_num }]
              }
            },
            {
              titulo: 'Importe adjudicado en contratos mayores', sub: 'Euros sin IVA',
              chips: [CHIP_MAY], fuente: FUENTE, nota: SIN_IVA,
              spec: {
                type: 'bar', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'eur', xTodas: true,
                series: [{ name: 'Adjudicado', data: r.imp_mayores }]
              }
            },
            {
              titulo: 'Importe adjudicado en contratos menores', sub: 'Euros con IVA',
              chips: [CHIP_MEN], fuente: FUENTE, nota: CON_IVA,
              spec: {
                type: 'bar', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'eur', xTodas: true,
                series: [{ name: 'Adjudicado', data: r.imp_menores }]
              }
            }
          ]
        };
      }
    },

    /* --------------------------------------------------- Contratos mayores */
    {
      id: 'mayores', nombre: 'Contratos mayores',
      titulo: 'Lo que se licita',
      desc: 'El <b>Listado Anual de Contratos celebrados</b> —el indicador nº 48— recoge los contratos que superan los umbrales del contrato menor. Cada fila es un contrato o un lote, con su presupuesto de licitación, su importe de adjudicación y el número de licitadores que se presentaron.',
      render: function () {
        var m = D.mayores || {}, r = D.resumen || {}, x = m.x || [];
        var i = ult(x), iR = idx(r.x, M.anio_max_may);
        return {
          nota: 'Serie ' + M.anio_min_may + '–' + M.anio_max_may + '. ' + SIN_IVA + ' ' +
            F.num(m.n_lotes) + ' de las ' + F.num(M.n_mayores) + ' filas son lotes de un mismo contrato, ' +
            'así que hay menos expedientes que filas.',
          kpis: [
            { label: 'Contratos en ' + M.anio_max_may, valor: en(r.n_mayores, iR), formato: F.num,
              delta: delta(r.n_mayores, iR), deltaRef: 'interanual', serie: r.n_mayores },
            { label: 'Adjudicado en ' + M.anio_max_may, valor: en(m.adjudicado, i), formato: eurM,
              delta: delta(m.adjudicado, i), deltaRef: 'interanual', serie: m.adjudicado },
            { label: 'Importe medio por contrato', valor: en(m.importe_medio, i),
              formato: function (v) { return F.eur(v); } },
            { label: 'Baja de adjudicación en ' + M.anio_max_may, valor: en(r.baja, iR),
              unidad: '%', dec: 1, serie: r.baja }
          ],
          cards: [
            {
              titulo: 'Presupuesto de licitación frente a lo adjudicado', sub: 'Euros sin IVA',
              chips: [CHIP_MAY], fuente: FUENTE, ancho: 'full',
              nota: 'La diferencia entre las dos barras es la baja de adjudicación: cuánto se rebaja respecto al precio de salida.',
              spec: {
                type: 'bar', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'eur', xTodas: true,
                series: [
                  { name: 'Presupuesto de licitación', data: m.licitacion },
                  { name: 'Importe adjudicado', data: m.adjudicado }
                ]
              }
            },
            {
              titulo: 'Contratos por tipo', sub: 'Número de contratos, serie anual',
              chips: [CHIP_MAY], fuente: FUENTE, ancho: 'full', nota: NOTA_TIPOS,
              spec: {
                type: 'stack', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'num', xTodas: true,
                series: series(m.tipos, m.n_tipo)
              }
            },
            {
              titulo: 'Importe por tipo de contrato', sub: 'Euros sin IVA, serie anual',
              chips: [CHIP_MAY], fuente: FUENTE, ancho: 'full', nota: SIN_IVA,
              spec: {
                type: 'stack', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'eur', xTodas: true,
                series: series(m.tipos, m.imp_tipo)
              }
            },
            {
              titulo: 'Procedimiento de adjudicación', sub: 'Número de contratos, serie anual',
              chips: [CHIP_MAY], fuente: FUENTE, ancho: 'full',
              nota: 'El procedimiento abierto es el que garantiza más concurrencia. El negociado sin publicidad y el de emergencia son las excepciones, y conviene mirar cuánto pesan.',
              spec: {
                type: 'stack', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'num', xTodas: true,
                series: series(m.procedimientos, m.n_proc)
              }
            },
            {
              titulo: 'Importe por procedimiento', sub: 'Euros sin IVA, serie anual',
              chips: [CHIP_MAY], fuente: FUENTE, ancho: 'full', nota: SIN_IVA,
              spec: {
                type: 'stack', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'eur', xTodas: true,
                series: series(m.procedimientos, m.imp_proc)
              }
            },
            {
              titulo: 'Importe medio por contrato', sub: 'Euros sin IVA',
              chips: [CHIP_MAY], fuente: FUENTE,
              spec: {
                type: 'bar', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'eur', xTodas: true,
                series: [{ name: 'Importe medio', data: m.importe_medio }]
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
      desc: 'El contrato menor —hasta 15.000 € en servicios y suministros y 40.000 € en obras— se adjudica directamente, sin concurrencia. El Ayuntamiento publica <b>relaciones trimestrales</b> y, algunos años, un listado anual. Aquí mandan las trimestrales: su suma coincide con los totales que el propio Ayuntamiento certifica.',
      render: function () {
        var m = D.menores || {}, r = D.resumen || {}, x = m.x || [];
        var i = ult(x), t = m.trimestres || {}, iR = idx(r.x, M.anio_max_men);
        return {
          nota: 'Serie ' + M.anio_min_men + '–' + M.anio_max_men + '. ' + CON_IVA +
            ' El reparto por trimestre solo existe en los ejercicios con relaciones trimestrales publicadas (' +
            (t.anios || []).join(', ') + '); en el resto el Ayuntamiento solo publicó el listado anual.',
          kpis: [
            { label: 'Contratos menores en ' + M.anio_max_men, valor: en(r.n_menores, iR), formato: F.num,
              delta: delta(r.n_menores, iR), deltaRef: 'interanual', serie: r.n_menores },
            { label: 'Importe en ' + M.anio_max_men, valor: en(r.imp_menores, iR), formato: eurM,
              delta: delta(r.imp_menores, iR), deltaRef: 'interanual', serie: r.imp_menores },
            { label: 'Importe medio por contrato', valor: en(m.importe_medio, i),
              formato: function (v) { return F.eur(v); } },
            { label: 'Proveedores distintos de menores', valor: (D.empresas || {}).n_solo_menores, formato: F.num }
          ],
          cards: [
            {
              titulo: 'Contratos menores por tipo', sub: 'Número de contratos, serie anual',
              chips: [CHIP_MEN], fuente: FUENTE, ancho: 'full', nota: NOTA_TIPOS,
              spec: {
                type: 'stack', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'num', xTodas: true,
                series: series(m.tipos, m.n_tipo)
              }
            },
            {
              titulo: 'Importe de los contratos menores por tipo', sub: 'Euros con IVA, serie anual',
              chips: [CHIP_MEN], fuente: FUENTE, ancho: 'full', nota: CON_IVA,
              spec: {
                type: 'stack', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'eur', xTodas: true,
                series: series(m.tipos, m.imp_tipo)
              }
            },
            {
              titulo: 'Reparto por trimestre', sub: 'Importe adjudicado en cada trimestre, euros con IVA',
              chips: [CHIP_MEN], fuente: FUENTE, ancho: 'full',
              nota: 'La concentración en el cuarto trimestre es el patrón habitual del cierre presupuestario: conviene mirarla año a año.',
              spec: {
                type: 'bar', xType: 'cat', xLabel: 'Trimestre', x: t.x, yFormat: 'eur', xTodas: true,
                series: (t.anios || []).map(function (a, k) {
                  return { name: String(a), data: (t.importe || [])[k] };
                })
              }
            },
            {
              titulo: 'Importe medio por contrato menor', sub: 'Euros con IVA',
              chips: [CHIP_MEN], fuente: FUENTE,
              spec: {
                type: 'bar', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'eur', xTodas: true,
                series: [{ name: 'Importe medio', data: m.importe_medio }]
              }
            },
            {
              titulo: 'Mayores proveedores de contratos menores', sub: 'Euros con IVA, acumulado del periodo',
              chips: [CHIP_MEN], fuente: FUENTE, ancho: 'full', alto: 'tall',
              nota: 'Los nombres se toman tal cual los publica el Ayuntamiento: una misma empresa puede figurar con grafías distintas y aparecer dos veces.',
              spec: {
                type: 'barh', x: ((D.empresas || {}).top_menores || {}).x, yFormat: 'eur', xLabel: 'Proveedor',
                series: [{ name: 'Importe adjudicado', data: ((D.empresas || {}).top_menores || {}).v }]
              }
            }
          ]
        };
      }
    },

    /* ------------------------------------------------------- Modificados -- */
    {
      id: 'modificados', nombre: 'Modificados',
      titulo: 'Lo que crece después de adjudicarse',
      desc: 'La <b>Relación de Modificados</b> —indicador nº 50— recoge los contratos que se amplían una vez adjudicados. Es de los indicadores más reveladores de un sistema de contratación: un contrato que se adjudica barato y luego se modifica al alza no salió barato.',
      render: function () {
        var o = D.modificados || {}, x = o.x || [];
        var i = ult(x);
        return {
          nota: 'Serie ' + M.anio_min_mod + '–' + M.anio_max_mod + '. Importes sin IVA, como los publica el listado. ' +
            'El porcentaje se calcula sobre el importe adjudicado en contratos mayores del mismo año, que es la base comparable.',
          kpis: [
            { label: 'Modificados en ' + M.anio_max_mod, valor: en(o.n, i), formato: F.num,
              delta: delta(o.n, i), deltaRef: 'interanual', invertir: true, serie: o.n },
            { label: 'Importe modificado en ' + M.anio_max_mod, valor: en(o.importe, i), formato: eurM,
              delta: delta(o.importe, i), deltaRef: 'interanual', invertir: true, serie: o.importe },
            { label: 'Sobre lo adjudicado en mayores', valor: en(o.pct_sobre_adjudicado, i), unidad: '%', dec: 2,
              invertir: true, serie: o.pct_sobre_adjudicado },
            { label: 'Acumulado ' + M.anio_min_mod + '–' + M.anio_max_mod, valor: M.imp_modificados, formato: eurM }
          ],
          cards: [
            {
              titulo: 'Modificados por año', sub: 'Número de contratos modificados',
              chips: [CHIP_MOD], fuente: FUENTE,
              spec: {
                type: 'bar', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'num', xTodas: true,
                series: [{ name: 'Modificados', data: o.n }]
              }
            },
            {
              titulo: 'Importe de las modificaciones', sub: 'Euros sin IVA',
              chips: [CHIP_MOD], fuente: FUENTE,
              spec: {
                type: 'bar', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'eur', xTodas: true,
                series: [{ name: 'Importe modificado', data: o.importe }]
              }
            },
            {
              titulo: 'Peso de las modificaciones', sub: 'Porcentaje sobre el importe adjudicado en contratos mayores',
              chips: [CHIP_MOD], fuente: FUENTE, ancho: 'full',
              nota: 'Un año con pocos modificados publicados no significa necesariamente que no los hubiera: significa que eso es lo que se publicó.',
              spec: {
                type: 'line', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'pct', xTodas: true,
                series: [{ name: 'Modificados sobre adjudicado', data: o.pct_sobre_adjudicado }]
              }
            },
            {
              titulo: 'Las mayores modificaciones del periodo', sub: 'Euros sin IVA',
              chips: [CHIP_MOD], fuente: FUENTE, ancho: 'full', alto: 'tall',
              nota: 'Cada barra es un expediente. El objeto completo está en el buscador, filtrando por «Modificados».',
              spec: {
                type: 'barh', x: (o.top || {}).x, yFormat: 'eur', xLabel: 'Expediente',
                series: [{ name: 'Importe de la modificación', data: (o.top || {}).v }]
              }
            }
          ]
        };
      }
    },

    /* ----------------------------------------------------- Adjudicatarios - */
    {
      id: 'empresas', nombre: 'Adjudicatarios',
      titulo: 'Quién cobra',
      desc: 'Empresas y profesionales que aparecen como adjudicatarios. Los dos rankings de importe van por separado —mayores sin IVA, menores con IVA— porque sumarlos daría una cifra que no significa nada. El recuento de contratos sí es conjunto.',
      render: function () {
        var e = D.empresas || {};
        return {
          nota: 'Los nombres se toman tal cual vienen publicados. Una misma empresa puede figurar con grafías distintas —con y sin «S.L.», con comas de más— y contar dos veces: aquí no se fusionan por parecido, porque eso sería inventar adjudicatarios.',
          kpis: [
            { label: 'Adjudicatarios distintos', valor: e.n_distintas, formato: F.num },
            { label: 'Aparecen en contratos mayores', valor: e.n_solo_mayores, formato: F.num },
            { label: 'Aparecen en contratos menores', valor: e.n_solo_menores, formato: F.num },
            { label: 'Los 10 primeros, sobre el importe en mayores', valor: e.concentracion_may, unidad: '%', dec: 1 }
          ],
          cards: [
            {
              titulo: 'Mayores adjudicatarios en contratos mayores', sub: 'Euros sin IVA, acumulado del periodo',
              chips: [CHIP_MAY], fuente: FUENTE, ancho: 'full', alto: 'tall', nota: SIN_IVA,
              spec: {
                type: 'barh', x: (e.top_mayores || {}).x, yFormat: 'eur', xLabel: 'Adjudicatario',
                series: [{ name: 'Importe adjudicado', data: (e.top_mayores || {}).v }]
              }
            },
            {
              titulo: 'Quién firma más contratos', sub: 'Número de contratos, mayores y menores juntos',
              chips: [{ txt: 'Mayores y menores' }], fuente: FUENTE, ancho: 'full', alto: 'tall',
              nota: 'Aquí sí se suman las dos clases, porque contar expedientes no depende del IVA.',
              spec: {
                type: 'barh', x: (e.top_numero || {}).x, yFormat: 'num', xLabel: 'Adjudicatario',
                series: [{ name: 'Nº de contratos', data: (e.top_numero || {}).v }]
              }
            }
          ]
        };
      }
    },

    /* -------------------------------------------------------- Competencia - */
    {
      id: 'competencia', nombre: 'Competencia',
      titulo: 'Cuánta concurrencia hay',
      desc: 'El listado anual publica cuántos licitadores se presentaron a cada contrato mayor. Es el dato que permite saber si las licitaciones atraen ofertas o se resuelven con una sola.',
      render: function () {
        var c = D.competencia || {}, r = D.resumen || {}, x = c.x || [];
        var i = ult(x);
        return {
          nota: 'Todo lo de esta sección se calcula <b>solo sobre los contratos en los que consta el número de licitadores</b>. La última tarjeta dice cuántos son: si la cobertura es baja, los porcentajes de arriba valen menos.',
          kpis: [
            { label: 'Media de licitadores en ' + M.anio_max_may, valor: en(c.media, i), dec: 1,
              delta: delta(c.media, i), deltaRef: 'interanual', serie: c.media },
            { label: 'Adjudicados con una sola oferta', valor: en(c.pct_una, i), unidad: '%', dec: 1,
              delta: delta(c.pct_una, i), deltaRef: 'interanual', invertir: true, serie: c.pct_una },
            { label: 'Baja de adjudicación', valor: en(r.baja, idx(r.x, M.anio_max_may)),
              unidad: '%', dec: 1, serie: r.baja },
            { label: 'Contratos con el dato informado', valor: en(c.pct_informados, i), unidad: '%', dec: 1,
              serie: c.pct_informados }
          ],
          cards: [
            {
              titulo: 'Media de licitadores por contrato', sub: 'Contratos mayores',
              chips: [CHIP_MAY], fuente: FUENTE,
              spec: {
                type: 'line', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'num', xTodas: true,
                series: [{ name: 'Licitadores por contrato', data: c.media }]
              }
            },
            {
              titulo: 'Contratos con una sola oferta', sub: 'Porcentaje sobre los contratos con el dato informado',
              chips: [CHIP_MAY], fuente: FUENTE,
              nota: 'Una sola oferta no es ilegal ni implica irregularidad, pero deja el precio sin contraste.',
              spec: {
                type: 'line', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'pct', xTodas: true,
                series: [{ name: 'Con una sola oferta', data: c.pct_una }]
              }
            },
            {
              titulo: 'Baja de adjudicación', sub: 'Cuánto se rebaja el precio de salida, en porcentaje',
              chips: [CHIP_MAY], fuente: FUENTE,
              nota: 'Se agrega por importes, no promediando porcentajes: un contrato de un millón pesa lo que vale.',
              spec: {
                type: 'line', xType: 'anual', xLabel: 'Año', x: r.x, yFormat: 'pct', xTodas: true,
                series: [{ name: 'Baja media', data: r.baja }]
              }
            },
            {
              titulo: 'Cobertura del indicador', sub: 'Contratos en los que consta el número de licitadores',
              chips: [CHIP_MAY], fuente: FUENTE,
              nota: 'Esto no es un dato de contratación, es la calidad del dato: cuanto más baja, menos representativas son las tres tarjetas anteriores.',
              spec: {
                type: 'line', xType: 'anual', xLabel: 'Año', x: x, yFormat: 'pct', xTodas: true,
                series: [{ name: 'Con el dato informado', data: c.pct_informados }]
              }
            }
          ]
        };
      }
    },

    /* ---------------------------------------------------------- Buscador -- */
    {
      id: 'buscador', nombre: 'Buscar contrato',
      titulo: 'Buscar un contrato',
      desc: 'Todos los registros publicados, uno a uno: mayores, menores y modificados. Se puede buscar por objeto, expediente, adjudicatario o NIF, filtrar y descargar la selección en CSV. Cada ficha enlaza al documento del que sale.',
      render: function () { return { extra: Buscador.html() }; }
    },

    /* --------------------------------------------------------- Documentos - */
    {
      id: 'documentos', nombre: 'Documentos fuente',
      titulo: 'De dónde sale cada cifra',
      desc: 'Los documentos del perfil del contratante que alimentan este observatorio, con el enlace directo a cada uno y cuántas filas aporta. Si un número de arriba no cuadra, se puede abrir el PDF y comprobarlo.',
      render: function () {
        var docs = M.documentos || [];
        var nombre = { mayores: 'Contratos mayores', menores: 'Contratos menores', modificados: 'Modificados' };
        var filas = docs.map(function (d) {
          return '<tr>' +
            '<td><span class="obs-chip brand">' + esc(nombre[d.clase] || d.clase) + '</span></td>' +
            '<td class="bs-anio">' + esc(d.anio) + (d.trimestre ? ' · T' + d.trimestre : '') + '</td>' +
            '<td>' + esc(d.titulo) + '</td>' +
            '<td class="bs-num">' + F.num(d.filas) + '</td>' +
            '<td>' + esc(d.publicado) + '</td>' +
            '<td><a href="' + esc(d.url) + '" target="_blank" rel="noopener">Abrir ' + Obs.icono.externo() + '</a></td>' +
            '</tr>';
        }).join('');
        return {
          nota: 'Son ' + F.num(docs.length) + ' documentos, el más reciente publicado el ' + esc(M.ultimo_documento) +
            '. Los listados anuales de contratos menores de los ejercicios que también tienen relaciones trimestrales ' +
            'no se usan: se contarían dos veces.',
          extra: '<div class="bs-tabla-wrap"><table class="obs-table bs-tabla">' +
            '<thead><tr><th>Clase</th><th>Ejercicio</th><th>Documento</th>' +
            '<th class="bs-num">Filas</th><th>Publicado</th><th>Enlace</th></tr></thead>' +
            '<tbody>' + filas + '</tbody></table></div>'
        };
      }
    }
  ];

  /* ----------------------------------------------------------- Arranque -- */

  Obs.init({
    titulo: 'Observatorio de Transparencia en la Contratación',
    subtitulo: 'Ayuntamiento de Marbella · mayores ' + M.anio_min_may + '–' + M.anio_max_may +
      ' · menores ' + M.anio_min_men + '–' + M.anio_max_men,
    secciones: SECCIONES,
    actualizado: M.actualizado,
    fuentes: [
      FUENTE,
      { txt: 'Plataforma de Contratación del Sector Público',
        url: 'https://contrataciondelestado.es/wps/portal/plataforma' },
      { txt: 'Artículo 63 LCSP · perfil del contratante',
        url: 'https://www.boe.es/buscar/act.php?id=BOE-A-2017-12902&p=20171109&tn=1#a63' }
    ],
    metodologia:
      '<b>Fuente única.</b> Los documentos que el Ayuntamiento de Marbella publica en la pestaña «Documentos» de ' +
      'su <a href="https://contrataciondelestado.es/wps/portal/perfilContratante" target="_blank" rel="noopener">perfil ' +
      'del contratante</a> en la Plataforma de Contratación del Sector Público, que es donde el artículo 63 de la LCSP ' +
      'le obliga a publicarlos. Un proceso automático los descarga, extrae las tablas de cada PDF y las agrega. ' +
      'La sección «Documentos fuente» lista los ' + F.num(M.n_documentos) + ' que se están usando, con su enlace. ' +
      '<br><br><b>Contratos mayores.</b> Listado Anual de Contratos celebrados, indicador nº 48 ' +
      '(' + M.anio_min_may + '–' + M.anio_max_may + '). <b>Contratos menores.</b> Relaciones trimestrales ' +
      '(' + M.anio_min_men + '–' + M.anio_max_men + '); donde un ejercicio solo tiene listado anual se usa ese. ' +
      'Cuando existen las dos cosas mandan las trimestrales, porque su suma coincide con los totales que el ' +
      'Ayuntamiento certifica. <b>Modificados.</b> Relación de Modificados, indicador nº 50. ' +
      '<br><br><b>Sobre el IVA.</b> El listado de mayores publica los importes <b>sin IVA</b> y el de menores ' +
      '<b>con IVA</b>. Ninguno incluye la otra base, así que el observatorio no da ninguna cifra que sume las dos ' +
      'clases en euros; cada gráfica dice con qué base está.',
    pie: 'El observatorio refleja lo que el Ayuntamiento publica. Un contrato tramitado y no incluido en estos ' +
      'listados no aparece, y los campos que el listado deja vacíos —número de licitadores, algún importe— quedan ' +
      'fuera de los indicadores que dependen de ellos. Los nombres de los adjudicatarios se reproducen tal cual, ' +
      'sin fusionar grafías. Las series terminan donde termina el último documento publicado: mayores en ' +
      M.anio_max_may + ' y menores en ' + M.anio_max_men + '.'
  });

  Buscador.enganchar(document.getElementById('obs-app'));

  Obs.estado('Último documento publicado: ' + (M.ultimo_documento || '—') + ' · ' +
    F.num(M.n_mayores) + ' mayores, ' + F.num(M.n_menores) + ' menores y ' +
    F.num(M.n_modificados) + ' modificados', 'live');

})();
