#!/usr/bin/env python3
"""Genera la cadena "papelera" de Pokémon GO (juego en español) y una página para copiarla.

Uso: python3 generar_papelera.py <carpeta_pvpoke> <game_master.json> [timestamp_game_master.txt]

La cadena muestra los Pokémon que puedes transferir. Deja fuera:
  - Las familias completas del meta PvP (top N de cada liga según PvPoke) y las de "siempre_guardar".
  - De las familias de los mejores atacantes de incursión por tipo, los que tienen 11-15 de ataque.
  - Los de 4 estrellas, variocolor, oscuros, legendarios, singulares, ultraentes, con disfraz,
    con fondo, dinamax, gigamax, con ataques especiales, intercambiados y cualquier etiquetado.

Datos: PvPoke (github.com/pvpoke/pvpoke) y game master (github.com/PokeMiners/game_masters).
Solo usa la biblioteca estándar de Python.
"""
import datetime as dt
import html
import json
import math
import os
import re
import sys
from collections import defaultdict

PVPOKE = sys.argv[1] if len(sys.argv) > 1 else 'data/pvpoke'
GM = sys.argv[2] if len(sys.argv) > 2 else 'data/gm/latest.json'
GM_TS = sys.argv[3] if len(sys.argv) > 3 else None
AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, 'docs')

cfg = json.load(open(os.path.join(AQUI, 'config.json'), encoding='utf-8'))
LIGAS = {  # clave de config -> (fichero de ranking de PvPoke, nombre para mostrar)
    'liga_500': ('little/overall/rankings-500.json', 'Liga de 500 PC'),
    'super_ball': ('all/overall/rankings-1500.json', 'Liga Super Ball'),
    'ultra_ball': ('all/overall/rankings-2500.json', 'Liga Ultra Ball'),
    'master_ball': ('all/overall/rankings-10000.json', 'Liga Master Ball'),
}
CPM40 = 0.7903
DEF_OBJETIVO = 160.0
MOVS_EXCLUIDOS = {'RETURN', 'FRUSTRATION'}
CLASES_ESPECIALES = {'POKEMON_CLASS_LEGENDARY', 'POKEMON_CLASS_MYTHIC', 'POKEMON_CLASS_ULTRA_BEAST'}
TIPOS = {'NORMAL': 'Normal', 'FIRE': 'Fuego', 'WATER': 'Agua', 'GRASS': 'Planta', 'ELECTRIC': 'Eléctrico',
         'ICE': 'Hielo', 'FIGHTING': 'Lucha', 'POISON': 'Veneno', 'GROUND': 'Tierra', 'FLYING': 'Volador',
         'PSYCHIC': 'Psíquico', 'BUG': 'Bicho', 'ROCK': 'Roca', 'GHOST': 'Fantasma', 'DRAGON': 'Dragón',
         'DARK': 'Siniestro', 'STEEL': 'Acero', 'FAIRY': 'Hada'}
PROTECCIONES = ('&!variocolor&!oscuro&!legendario&!singular&!ultraentes&!ultraente&!disfraz&!fondo'
                '&!dinamax&!gigamax&!@especial&!intercambiados&!#')

# ---------- game master: ataques PvE, estadísticas y familias ----------
gm = json.load(open(GM, encoding='utf-8'))
movs = {}
for x in gm:
    d = x['data']
    if 'moveSettings' in d:
        ms = d['moveSettings']
        movs[ms['movementId']] = ms
        m = re.match(r'V\d{4}_MOVE_(.+)', x['templateId'])
        if m:
            movs.setdefault(m.group(1), ms)

pokes = []
for x in gm:
    d = x['data']
    m = re.match(r'V(\d{4})_POKEMON_', x['templateId'])
    if 'pokemonSettings' in d and m:
        s = d['pokemonSettings']
        s['_dex'] = int(m.group(1))
        pokes.append(s)

familia_de, dex_de_familia, dex_especiales = {}, defaultdict(set), set()
for s in pokes:
    if s.get('familyId'):
        familia_de.setdefault(s['_dex'], s['familyId'])
        dex_de_familia[s['familyId']].add(s['_dex'])
    if s.get('pokemonClass') in CLASES_ESPECIALES:
        dex_especiales.add(s['_dex'])

# ---------- PvPoke: meta PvP actual ----------
pv = json.load(open(f'{PVPOKE}/gamemaster.json', encoding='utf-8'))
pv_por_id = {p['speciesId']: p for p in pv['pokemon']}
dex_publicados = {p['dex'] for p in pv['pokemon'] if p.get('released')}
pv_familias = defaultdict(set)
for p in pv['pokemon']:
    if (p.get('family') or {}).get('id'):
        pv_familias[p['family']['id']].add(p['dex'])


def familia(dex):
    if dex in familia_de:
        return set(dex_de_familia[familia_de[dex]])
    for ds in pv_familias.values():  # especies más nuevas que el game master
        if dex in ds:
            return set(ds)
    return {dex}


pvp_guardar, pvp_lista = set(), {}
for clave, n in cfg['top_pvp'].items():
    fichero, nombre = LIGAS[clave]
    lista = []
    for e in json.load(open(f'{PVPOKE}/rankings/{fichero}', encoding='utf-8'))[:n]:
        p = pv_por_id.get(e['speciesId'])
        if not p:
            continue
        fam = familia(p['dex'])
        if all(d in dex_especiales for d in fam):  # ya protegidos por !legendario, etc.
            continue
        pvp_guardar |= fam
        lista.append(p['speciesName'])
    pvp_lista[nombre] = lista
siempre = []
for sid in cfg.get('siempre_guardar', []):
    p = pv_por_id.get(sid.lower())
    if p:
        pvp_guardar |= familia(p['dex'])
        siempre.append(p['speciesName'])
    else:
        print(f'Aviso: no encuentro "{sid}" en PvPoke (usa el nombre en inglés, p. ej. "stunfisk_galarian")',
              file=sys.stderr)

# ---------- atacantes de incursión por tipo (estimador DPS/TDO a nivel 40, 15/15/15) ----------


def rating(base, tipos, rapido, cargado):
    atk = (base['baseAttack'] + 15) * CPM40
    dfn = (base['baseDefense'] + 15) * CPM40
    ps = math.floor((base['baseStamina'] + 15) * CPM40)

    def dano(mv):
        stab = 1.2 if mv['pokemonType'] in tipos else 1.0
        return 0.5 * mv.get('power', 0) * atk / DEF_OBJETIVO * stab * 1.6 + 0.5

    fd, fe = rapido['durationMs'] / 1000, rapido.get('energyDelta', 0)
    cd, ce = cargado['durationMs'] / 1000, -cargado.get('energyDelta', 0)
    if fe <= 0 or ce <= 0:
        return None
    y = 900 / dfn
    fdps, feps, cdps = dano(rapido) / fd, fe / fd, dano(cargado) / cd
    ce_ef = ce + (0.5 * fe + 0.5 * y * cargado.get('damageWindowStartMs', 0) / 1000 if ce >= 100 else 0)
    ceps = ce_ef / cd
    x = 0.5 * ce + 0.5 * fe
    dps = (fdps * ceps + cdps * feps) / (ceps + feps) + ((cdps - fdps) / (ceps + feps)) * (0.5 - x / ps) * y
    dps = max(dps, fdps)
    return (dps ** 3 * dps * ps / y) ** 0.25


def ataques(s, rapidos):
    claves = ['quickMoves', 'eliteQuickMove'] if rapidos else ['cinematicMoves', 'eliteCinematicMove']
    return [movs[m] for k in claves for m in (s.get(k) or [])
            if m in movs and str(movs[m]['movementId']) not in MOVS_EXCLUIDOS]


def bonito(nombre):
    nombre = re.sub(r'_NORMAL$', '', str(nombre)).replace('MEGA_X', 'MEGA X').replace('MEGA_Y', 'MEGA Y')
    return nombre.replace('_', ' ').title()


puntuaciones = defaultdict(list)
for s in pokes:
    dex = s['_dex']
    if dex in dex_especiales or dex not in dex_publicados or not (s.get('stats') or {}).get('baseAttack'):
        continue
    variantes = [(s['stats'], {s.get('type'), s.get('type2')}, s.get('form') or s.get('pokemonId'))]
    for o in s.get('tempEvoOverrides') or []:
        if o.get('stats') and o.get('tempEvoId'):
            variantes.append((o['stats'], {o.get('typeOverride1'), o.get('typeOverride2')},
                              f"{o['tempEvoId'].replace('TEMP_EVOLUTION_', '')} {s.get('pokemonId')}"))
    rapidos, cargados = ataques(s, True), ataques(s, False)
    for stats, tipos, nombre in variantes:
        for t in TIPOS:
            pt = f'POKEMON_TYPE_{t}'
            mejor = max((rating(stats, tipos, f, c) or 0 for f in rapidos if f['pokemonType'] == pt
                         for c in cargados if c['pokemonType'] == pt), default=0)
            if mejor:
                puntuaciones[t].append((mejor, bonito(nombre), dex))

atacantes_guardar, atacantes_lista = set(), {}
for t, nombre_tipo in TIPOS.items():
    vistas, top = set(), []
    for _, nombre, dex in sorted(puntuaciones[t], key=lambda x: (-x[0], len(x[1]))):  # empate: forma normal
        fam = familia_de.get(dex, dex)
        if fam in vistas:
            continue
        vistas.add(fam)
        top.append(nombre)
        atacantes_guardar |= familia(dex)
        if len(top) == cfg['top_atacantes_por_tipo']:
            break
    atacantes_lista[nombre_tipo] = top
solo_atacantes = atacantes_guardar - pvp_guardar

# ---------- cadena ----------


def rangos(nums):
    nums, out, i = sorted(nums), [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(f'{nums[i]}' if i == j else f'{nums[i]}-{nums[j]}')
        i = j + 1
    return out


cadena = '&'.join([cfg['estrellas_papelera'] + PROTECCIONES]
                  + [f'!{r}' for r in rangos(pvp_guardar)]
                  + [f'!{r},0-2ataque' for r in rangos(solo_atacantes)])

ahora = dt.datetime.now(dt.timezone.utc)
try:
    from zoneinfo import ZoneInfo
    ahora_local, zona = ahora.astimezone(ZoneInfo('Europe/Madrid')), 'hora de España'
except Exception:
    ahora_local, zona = ahora, 'UTC'
digitos = sorted(int(c) for c in re.findall(r'([0-4])\*', cfg['estrellas_papelera']))
texto_estrellas = (f'{digitos[0]} a {digitos[-1]} estrellas' if digitos == list(range(digitos[0], digitos[-1] + 1))
                   else ', '.join(f'{d}' for d in digitos) + ' estrellas')
datos_juego = None
if GM_TS and os.path.exists(GM_TS):
    try:
        datos_juego = dt.datetime.fromtimestamp(int(open(GM_TS).read().strip()) / 1000, dt.timezone.utc)
    except ValueError:
        pass

os.makedirs(SALIDA, exist_ok=True)
open(os.path.join(SALIDA, 'cadena.txt'), 'w', encoding='utf-8').write(cadena)
json.dump({'generada': ahora.isoformat(timespec='minutes'),
           'datos_juego': datos_juego.date().isoformat() if datos_juego else None,
           'longitud': len(cadena), 'cadena': cadena,
           'pvp_guardar': sorted(pvp_guardar), 'solo_atacantes': sorted(solo_atacantes),
           'siempre_guardar': siempre, 'meta_pvp': pvp_lista, 'atacantes': atacantes_lista},
          open(os.path.join(SALIDA, 'papelera.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---------- página ----------
e = html.escape
lista_pvp = ''.join(f'<h3>{e(liga)} <span>top {len(l)}</span></h3><p>{e(", ".join(l))}</p>'
                    for liga, l in pvp_lista.items())
lista_atk = ''.join(f'<tr><th>{e(t)}</th><td>{e(", ".join(l))}</td></tr>' for t, l in atacantes_lista.items())
pagina = f'''<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Papelera Pokémon GO</title>
<style>
:root{{color-scheme:light dark;--bg:#f6f7f9;--card:#fff;--txt:#1d2329;--sub:#5f6b76;--acc:#1f7a5a;--line:#dfe3e8}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111417;--card:#1b2025;--txt:#e9edf1;--sub:#98a4b0;--acc:#4cc38a;--line:#2b3238}}}}
*{{box-sizing:border-box}}body{{margin:0;font:16px/1.5 -apple-system,system-ui,sans-serif;background:var(--bg);color:var(--txt)}}
main{{max-width:680px;margin:0 auto;padding:20px 16px 48px}}h1{{font-size:24px;margin:8px 0 4px}}
.sub{{color:var(--sub);font-size:14px;margin:0 0 16px}}.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:14px}}
button{{width:100%;font-family:inherit;font-size:18px;font-weight:600;line-height:1;padding:16px;border:0;border-radius:12px;background:var(--acc);color:#fff;cursor:pointer}}
textarea{{width:100%;height:110px;margin-top:12px;font:12px/1.4 ui-monospace,Menlo,monospace;border:1px solid var(--line);border-radius:10px;padding:10px;background:var(--bg);color:var(--txt);resize:vertical}}
.ok{{color:var(--acc);font-weight:600;min-height:1.5em;margin:8px 0 0}}h2{{font-size:17px;margin:0 0 8px}}h3{{font-size:15px;margin:14px 0 2px}}h3 span{{color:var(--sub);font-weight:400;font-size:13px}}
p,li,td{{font-size:14px}}ol{{padding-left:20px;margin:0}}table{{border-collapse:collapse;width:100%}}th{{text-align:left;vertical-align:top;padding:6px 10px 6px 0;font-size:14px;white-space:nowrap}}td{{padding:6px 0;border-bottom:1px solid var(--line)}}
details summary{{cursor:pointer;font-weight:600}}
</style></head><body><main>
<h1>Papelera Pokémon GO</h1>
<p class="sub">Actualizada el {ahora_local:%d/%m/%Y a las %H:%M} ({zona}) · {len(cadena)} caracteres{f" · datos de incursiones del {datos_juego:%d/%m/%Y}" if datos_juego else ""}</p>
<div class="card"><button id="copiar">Copiar cadena</button><p class="ok" id="estado"></p>
<textarea id="cadena" readonly>{e(cadena)}</textarea></div>
<div class="card"><h2>Cómo usarla</h2><ol>
<li>Pégala en el buscador de tu almacenamiento de Pokémon.</li>
<li>Repasa la lista la primera vez y transfiere.</li>
<li>Mantén pulsada la búsqueda en las recientes para guardarla como favorita.</li></ol></div>
<div class="card"><h2>Qué protege</h2>
<p>Solo salen Pokémon de {texto_estrellas}. Se quedan fuera los especiales (variocolor, oscuros, legendarios, singulares, ultraentes, con disfraz o fondo, dinamax, gigamax, con ataques especiales e intercambiados) y todo lo que tenga etiqueta.</p>
<details><summary>Meta PvP: familias completas</summary>{lista_pvp}<h3>Siempre guardados</h3><p>{e(", ".join(siempre) or "Ninguno")}</p></details>
<details><summary>Atacantes de incursión: solo con 11–15 de ataque</summary><table>{lista_atk}</table></details></div>
<p class="sub">Datos: PvPoke y game master del juego (PokeMiners). Generada automáticamente.</p>
</main><script>
const b=document.getElementById('copiar'),t=document.getElementById('cadena'),s=document.getElementById('estado');
b.addEventListener('click',async()=>{{try{{await navigator.clipboard.writeText(t.value);s.textContent='Copiada. Pégala en el buscador del juego.'}}catch(_){{t.focus();t.select();t.setSelectionRange(0,t.value.length);s.textContent='Selecciónala y cópiala a mano.'}}}});
</script></body></html>'''
open(os.path.join(SALIDA, 'index.html'), 'w', encoding='utf-8').write(pagina)
print(f'OK · {len(cadena)} caracteres · {len(pvp_guardar)} dex PvP · {len(solo_atacantes)} dex atacantes')
