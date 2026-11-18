/* Motor de la papelera: construye la cadena de búsqueda de Pokémon GO (juego en español).
 * Lo usan la página (navegador) y construir.js (Node, en GitHub Actions). */
(function (root) {
  'use strict';

  const TALLA = [1, 5, 5, 4, 1]; // valores de IV que caben en cada banda: 0 | 1-5 | 6-10 | 11-14 | 15
  const MAX_DEX = 2000;
  const ESPECIALES = [
    ['variocolor', ['!variocolor']], ['oscuro', ['!oscuro']], ['legendario', ['!legendario']],
    ['singular', ['!singular']], ['ultraentes', ['!ultraentes', '!ultraente']], ['disfraz', ['!disfraz']],
    ['fondo', ['!fondo']], ['dinamax', ['!dinamax']], ['gigamax', ['!gigamax']],
    ['especial', ['!@especial']], ['intercambiados', ['!intercambiados']], ['etiquetados', ['!#']],
  ];
  const POR_DEFECTO = {
    estrellas_papelera: [0, 1, 2, 3], pc_maximo: null, pvp_minimo: 95,
    top_pvp: { liga_500: 50, super_ball: 50, ultra_ball: 50, master_ball: 30 },
    top_atacantes_por_tipo: 10, ataque_minimo_atacantes: 11, siempre_guardar: [],
    proteger: {
      variocolor: true, oscuro: true, legendario: true, singular: true, ultraentes: true, disfraz: true,
      fondo: true, dinamax: true, gigamax: true, especial: true, intercambiados: true, etiquetados: true,
      listos_para_liga: false, nundos: false, tamanos: false, evolucionables: false, unicos: false,
    },
  };

  function normalizar(cfg, base) {
    const b = JSON.parse(JSON.stringify(base || POR_DEFECTO));
    const c = cfg || {};
    const out = Object.assign({}, POR_DEFECTO, b, c);
    out.top_pvp = Object.assign({}, POR_DEFECTO.top_pvp, b.top_pvp, c.top_pvp);
    out.proteger = Object.assign({}, POR_DEFECTO.proteger, b.proteger, c.proteger);
    if (typeof out.estrellas_papelera === 'string') {
      out.estrellas_papelera = (out.estrellas_papelera.match(/[0-4](?=\*)/g) || []).map(Number);
    }
    out.siempre_guardar = (out.siempre_guardar || []).slice();
    return out;
  }

  // ---------- rangos de números de Pokédex ----------
  function rangos(nums) {
    const v = Array.from(new Set(nums)).sort((a, b) => a - b);
    const out = [];
    for (let i = 0; i < v.length;) {
      let j = i;
      while (j + 1 < v.length && v[j + 1] === v[j] + 1) j++;
      out.push([v[i], v[j]]);
      i = j + 1;
    }
    return out;
  }
  const txt = (r) => (r[0] === r[1] ? String(r[0]) : r[0] + '-' + r[1]);
  function complemento(rs) {
    const out = [];
    let desde = 1;
    for (const [a, b] of rs) {
      if (a > desde) out.push([desde, a - 1]);
      desde = b + 1;
    }
    if (desde <= MAX_DEX) out.push([desde, MAX_DEX]);
    return out;
  }

  // ---------- cajas de bandas (ataque, defensa, PS) ----------
  const suma = (i, j) => { let s = 0; for (let k = i; k <= j; k++) s += TALLA[k]; return s; };
  const peso = (a0, a1, d0, h0) => (a0 > a1 || d0 > 4 || h0 > 4 ? 0 : suma(a0, a1) * suma(d0, 4) * suma(h0, 4));
  const CAJAS = [];
  for (const [a0, a1] of [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4], [1, 4], [2, 4], [3, 4], [4, 4]]) {
    for (let d0 = 0; d0 < 5; d0++) {
      for (let h0 = 0; h0 < 5; h0++) {
        const m = new Uint32Array(4);
        for (let a = a0; a <= a1; a++) for (let d = d0; d < 5; d++) for (let h = h0; h < 5; h++) {
          const k = a * 25 + d * 5 + h;
          m[k >> 5] |= 1 << (k & 31);
        }
        CAJAS.push({ a0, a1, d0, h0, m, w: peso(a0, a1, d0, h0) });
      }
    }
  }
  const cubre = (r, m1, m2) => {
    for (let i = 0; i < 4; i++) if ((r[i] & ~(m1[i] | (m2 ? m2[i] : 0))) !== 0) return false;
    return true;
  };
  // Cubre las bandas buenas con 1 o 2 cajas, guardando lo mínimo posible de más.
  function cubrir(r) {
    let mejor = null;
    for (const c of CAJAS) if ((!mejor || c.w < mejor.w) && cubre(r, c.m)) mejor = { w: c.w, cajas: [c] };
    for (let i = 0; i < CAJAS.length; i++) {
      const c1 = CAJAS[i];
      for (let j = i + 1; j < CAJAS.length; j++) {
        const c2 = CAJAS[j];
        const w = c1.w + c2.w - peso(Math.max(c1.a0, c2.a0), Math.min(c1.a1, c2.a1), Math.max(c1.d0, c2.d0), Math.max(c1.h0, c2.h0));
        if (mejor && w >= mejor.w) continue;
        if (cubre(r, c1.m, c2.m)) mejor = { w, cajas: [c1, c2] };
      }
    }
    return mejor;
  }
  const claveCaja = (c) => [c.a0, c.a1, c.d0, c.h0].join('');
  function fueraDeCaja(c) { // términos que se cumplen cuando el Pokémon NO está en la caja
    const t = [];
    const r = (a, b, s) => (a === b ? a + s : a + '-' + b + s);
    if (!(c.a0 === 0 && c.a1 === 4)) t.push(c.a0 === 0 ? r(c.a1 + 1, 4, 'ataque') : r(0, c.a0 - 1, 'ataque'));
    if (c.d0 > 0) t.push(r(0, c.d0 - 1, 'defensa'));
    if (c.h0 > 0) t.push(r(0, c.h0 - 1, 'PS'));
    return t;
  }

  function familiasDe(datos, ids) {
    const porId = new Map(datos.especies.map((e) => [e[0], e]));
    const out = new Set();
    for (const id of ids) { const e = porId.get(String(id).toLowerCase()); if (e) out.add(e[3]); }
    return out;
  }

  // Bandas que llegan al mínimo de % en alguna liga elegida, por familia.
  function regiones(datos, cfg) {
    const T = Math.round(cfg.pvp_minimo * 10);
    const reg = new Map();
    for (const liga of datos.ligas) {
      const top = cfg.top_pvp[liga.id] || 0;
      for (const e of liga.ranking) {
        if (e.r > top || e.l) continue; // los legendarios ya los protege !legendario
        const m = reg.get(e.f) || new Uint32Array(4);
        for (let k = 0; k < e.t.length; k += 2) if (e.t[k + 1] >= T) m[e.t[k] >> 5] |= 1 << (e.t[k] & 31);
        reg.set(e.f, m);
      }
    }
    return reg;
  }

  // Los mejores atacantes de un tipo. Los legendarios (marcados con l) solo cuentan si se piden:
  // en la papelera ya los protege !legendario.
  const topTipo = (t, n, legendarios) => t.top.filter((a) => legendarios || !a.l).slice(0, n);

  function familiasAtacantes(datos, cfg) {
    const out = new Set();
    if (!(cfg.top_atacantes_por_tipo > 0) || !cfg.ataque_minimo_atacantes) return out;
    for (const t of datos.tipos) for (const a of topTipo(t, cfg.top_atacantes_por_tipo, false)) out.add(a.f);
    return out;
  }

  function construir(datos, cfgEntrada) {
    const cfg = normalizar(cfgEntrada, datos.config);
    const p = cfg.proteger;
    const partes = [];
    const add = (tipo, ...textos) => { for (const s of textos) partes.push({ tipo, s }); };
    const est = Array.from(new Set(cfg.estrellas_papelera)).filter((n) => n >= 0 && n <= 4).sort();
    if (!est.length) return { cadena: '', partes: [], error: 'Elige al menos una cantidad de estrellas.', cfg };
    add('limites', est.map((n) => n + '*').join(','));
    if (cfg.pc_maximo) add('limites', 'pc-' + cfg.pc_maximo);
    for (const [k, terminos] of ESPECIALES) if (p[k] !== false) add('especiales', ...terminos);
    if (p.tamanos) add('extra', '!xxl', '!xxs');
    if (p.evolucionables) add('extra', '!evolucionar');
    if (p.listos_para_liga) add('extra', '!pc1400-1500', '!pc2300-2500');
    if (p.nundos) add('extra', '1-4ataque,1-4defensa,1-4PS');
    if (p.unicos) add('extra', '!cantidad1');

    const siempre = familiasDe(datos, cfg.siempre_guardar);
    const dexSiempre = [];
    for (const f of siempre) dexSiempre.push(...datos.familias[f]);
    for (const r of rangos(dexSiempre)) add('siempre', '!' + txt(r));

    const reg = regiones(datos, cfg);
    const porCaja = new Map();
    let guardado = 0, nPvp = 0;
    for (const f of Array.from(reg.keys()).sort((a, b) => a - b)) {
      if (siempre.has(f)) continue;
      const c = cubrir(reg.get(f));
      guardado += c.w / 4096; nPvp++;
      for (const caja of c.cajas) {
        const k = claveCaja(caja);
        if (!porCaja.has(k)) porCaja.set(k, { caja, dex: [] });
        porCaja.get(k).dex.push(...datos.familias[f]);
      }
    }
    for (const k of Array.from(porCaja.keys()).sort()) {
      const { caja, dex } = porCaja.get(k);
      add('pvp', complemento(rangos(dex)).map(txt).concat(fueraDeCaja(caja)).join(','));
    }

    const atk = familiasAtacantes(datos, cfg);
    const dexAtk = [];
    for (const f of atk) if (!siempre.has(f)) dexAtk.push(...datos.familias[f]);
    if (dexAtk.length) {
      const banda = cfg.ataque_minimo_atacantes >= 15 ? 3 : 2;
      add('atacantes', complemento(rangos(dexAtk)).map(txt).concat('0-' + banda + 'ataque').join(','));
    }

    const cadena = partes.map((x) => x.s).join('&');
    return {
      cadena, partes, cfg,
      resumen: {
        longitud: cadena.length, familias_pvp: nPvp, guardado_pvp: nPvp ? guardado / nPvp : 0,
        familias_atacantes: atk.size, familias_siempre: siempre.size,
      },
    };
  }

  // ---------- búsquedas en positivo ----------
  const EJES = ['ataque', 'defensa', 'PS'];
  const LLENO = 31; // las 5 bandas
  function textoLiteral([eje, m]) { // bandas del eje -> "0-1ataque,3-4ataque"
    const t = [];
    for (let i = 0; i < 5; i++) {
      if (!(m >> i & 1)) continue;
      let j = i;
      while (j + 1 < 5 && (m >> (j + 1) & 1)) j++;
      t.push((i === j ? i : i + '-' + j) + EJES[eje]);
      i = j;
    }
    return t.join(',');
  }
  const literalesCaja = (c) => {
    const out = [];
    let ma = 0;
    for (let a = c.a0; a <= c.a1; a++) ma |= 1 << a;
    if (ma !== LLENO) out.push([0, ma]);
    if (c.d0 > 0) out.push([1, LLENO & ~((1 << c.d0) - 1)]);
    if (c.h0 > 0) out.push([2, LLENO & ~((1 << c.h0) - 1)]);
    return out;
  };
  // "Está dentro de las cajas" en forma de cláusulas (Y de O), como pide el buscador del juego.
  function clausulasCajas(cajas) {
    const x = literalesCaja(cajas[0]);
    if (cajas.length === 1) return x.map((l) => [l]);
    const y = literalesCaja(cajas[1]);
    if (!x.length || !y.length) return [];
    const out = [];
    for (const lx of x) for (const ly of y) {
      if (lx[0] === ly[0]) {
        const m = lx[1] | ly[1];
        if (m !== LLENO) out.push([[lx[0], m]]);
      } else out.push(lx[0] < ly[0] ? [lx, ly] : [ly, lx]);
    }
    return out;
  }
  // Rangos de Pokédex que incluyen todos los "si", ninguno de los "no" y lo que sea en el resto.
  function rangosCon(si, no) {
    const puntos = [];
    for (const d of si) puntos.push([d, 1]);
    for (const d of no) puntos.push([d, 0]);
    puntos.sort((a, b) => a[0] - b[0]);
    const out = [];
    let actual = null;
    for (const [d, bueno] of puntos) {
      if (!bueno) { actual = null; continue; }
      if (actual) actual[1] = d; else out.push(actual = [d, d]);
    }
    return out;
  }

  // Pokémon de las familias del meta que pueden llegar al mínimo de % en esas ligas.
  // Sale todo el que llega y algunos que se quedan cerca: el buscador solo ve las barras.
  function busquedaMeta(datos, op) {
    const T = Math.round((op.minimo || 0) * 10);
    const reg = new Map();
    for (const liga of datos.ligas) {
      const top = (op.top || {})[liga.id] || 0;
      if (!op.ligas.includes(liga.id) || !top) continue;
      for (const e of liga.ranking) {
        if (e.r > top || (e.l && !op.legendarios)) continue;
        const m = reg.get(e.f) || new Uint32Array(4);
        if (T) for (let k = 0; k < e.t.length; k += 2) if (e.t[k + 1] >= T) m[e.t[k] >> 5] |= 1 << (e.t[k] & 31);
        reg.set(e.f, m);
      }
    }
    const todas = [];
    for (const f of reg.keys()) todas.push(...datos.familias[f]);
    if (!todas.length) return { cadena: '', familias: 0 };
    const partes = [rangos(todas).map(txt).join(',')];
    if (T) {
      const grupos = new Map();
      for (const [f, r] of reg) {
        for (const cl of clausulasCajas(cubrir(r).cajas)) {
          const k = JSON.stringify(cl);
          if (!grupos.has(k)) grupos.set(k, { cl, dex: new Set() });
          for (const d of datos.familias[f]) grupos.get(k).dex.add(d);
        }
      }
      for (const k of Array.from(grupos.keys()).sort()) {
        const { cl, dex } = grupos.get(k);
        const fuera = rangosCon(todas.filter((d) => !dex.has(d)), dex).map(txt);
        partes.push(fuera.concat(cl.map(textoLiteral)).join(','));
      }
    }
    return { cadena: partes.join('&'), familias: reg.size };
  }

  // Familias de los mejores atacantes de un tipo (o de todos), en rangos de Pokédex.
  function busquedaAtacantes(datos, op) {
    const fams = new Set();
    for (const t of datos.tipos) {
      if (op.tipo && op.tipo !== 'todos' && op.tipo !== t.id) continue;
      for (const a of topTipo(t, op.top || 10, !!op.legendarios)) fams.add(a.f);
    }
    const dex = [];
    for (const f of fams) dex.push(...datos.familias[f]);
    return { cadena: rangos(dex).map(txt).join(','), familias: fams.size };
  }

  function dexMeta(datos, cfg) {
    cfg = normalizar(cfg, datos.config);
    const dex = [];
    for (const f of regiones(datos, cfg).keys()) dex.push(...datos.familias[f]);
    return rangos(dex).map(txt).join(',');
  }
  function dexAtacantes(datos, cfg) {
    cfg = normalizar(cfg, datos.config);
    const dex = [];
    for (const f of familiasAtacantes(datos, cfg)) dex.push(...datos.familias[f]);
    return rangos(dex).map(txt).join(',');
  }

  const api = { construir, normalizar, dexMeta, dexAtacantes, busquedaMeta, busquedaAtacantes, topTipo, rangos, txt, POR_DEFECTO, ESPECIALES };
  root.Papelera = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
