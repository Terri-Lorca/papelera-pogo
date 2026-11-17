// Construye docs/cadena.txt con los ajustes de config.json (lo que copia el atajo del iPhone).
const fs = require('fs');
const path = require('path');
const Papelera = require('./web/papelera.js');

const aqui = __dirname;
const datos = JSON.parse(fs.readFileSync(path.join(aqui, 'docs', 'datos.json'), 'utf8'));
const cfg = JSON.parse(fs.readFileSync(path.join(aqui, 'config.json'), 'utf8'));
const r = Papelera.construir(datos, cfg);
if (!r.cadena) {
  console.error(r.error);
  process.exit(1);
}
fs.writeFileSync(path.join(aqui, 'docs', 'cadena.txt'), r.cadena);
const s = r.resumen;
console.log(`OK · ${s.longitud} caracteres · ${s.familias_pvp} familias PvP (se guarda ~${Math.round(s.guardado_pvp * 100)} %) · ${s.familias_atacantes} familias de atacantes`);
