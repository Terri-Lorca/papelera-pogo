#!/usr/bin/env python3
"""Prepara los datos de la papelera de Pokémon GO y monta la página.

Uso: python3 generar_papelera.py <carpeta_pvpoke> <game_master.json> [timestamp_game_master.txt]

Escribe docs/datos.json y docs/index.html. La cadena la construye web/papelera.js
(la misma lógica en la página y en `node construir.js`, que escribe docs/cadena.txt).

Para cada Pokémon del meta PvP calcula, en su liga, el % de producto de estadísticas
respecto al rango 1 (como Poke Genie) de las 4096 combinaciones de IV y lo resume por
bandas de valoración (0, 1-5, 6-10, 11-14, 15), que es lo único que ve el buscador del juego.
Para incursiones ordena atacantes por tipo con un estimador DPS/TDO (nivel 40, 15/15/15).

Datos: PvPoke (github.com/pvpoke/pvpoke) y game master (github.com/PokeMiners/game_masters).
Solo usa la biblioteca estándar de Python.
"""
import bisect
import datetime as dt
import json
import math
import os
import re
import shutil
import sys
from collections import defaultdict

PVPOKE = sys.argv[1] if len(sys.argv) > 1 else 'data/pvpoke'
GM = sys.argv[2] if len(sys.argv) > 2 else 'data/gm/latest.json'
GM_TS = sys.argv[3] if len(sys.argv) > 3 else None
AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, 'docs')

LIGAS = [  # id, nombre, fichero de ranking de PvPoke, límite de PC
    ('liga_500', 'Liga de 500 PC', 'little/overall/rankings-500.json', 500),
    ('super_ball', 'Liga Super Ball', 'all/overall/rankings-1500.json', 1500),
    ('ultra_ball', 'Liga Ultra Ball', 'all/overall/rankings-2500.json', 2500),
    ('master_ball', 'Liga Master Ball', 'all/overall/rankings-10000.json', None),
]
TOP_MAX_PVP = 100       # el control de la página llega hasta aquí
TOP_MAX_ATACANTES = 15
PM_MINIMO = 900         # se exportan las bandas que pueden llegar al 90 % o más
CPM40 = 0.7903
DEF_OBJETIVO = 160.0
MOVS_EXCLUIDOS = {'RETURN', 'FRUSTRATION'}
CLASES_ESPECIALES = {'POKEMON_CLASS_LEGENDARY', 'POKEMON_CLASS_MYTHIC', 'POKEMON_CLASS_ULTRA_BEAST'}
TIPOS = {'NORMAL': 'Normal', 'FIRE': 'Fuego', 'WATER': 'Agua', 'GRASS': 'Planta', 'ELECTRIC': 'Eléctrico',
         'ICE': 'Hielo', 'FIGHTING': 'Lucha', 'POISON': 'Veneno', 'GROUND': 'Tierra', 'FLYING': 'Volador',
         'PSYCHIC': 'Psíquico', 'BUG': 'Bicho', 'ROCK': 'Roca', 'GHOST': 'Fantasma', 'DRAGON': 'Dragón',
         'DARK': 'Siniestro', 'STEEL': 'Acero', 'FAIRY': 'Hada'}

# ---------- game master: ataques PvE, estadísticas, familias y CPM ----------
gm = json.load(open(GM, encoding='utf-8'))
movs, pokes, cpm = {}, [], None
for x in gm:
    d = x['data']
    if 'moveSettings' in d:
        ms = d['moveSettings']
        movs[ms['movementId']] = ms
        m = re.match(r'V\d{4}_MOVE_(.+)', x['templateId'])
        if m:
            movs.setdefault(m.group(1), ms)
    elif 'pokemonSettings' in d:
        m = re.match(r'V(\d{4})_POKEMON_', x['templateId'])
        if m:
            d['pokemonSettings']['_dex'] = int(m.group(1))
            pokes.append(d['pokemonSettings'])
    elif 'playerLevel' in d and cpm is None:
        cpm = d['playerLevel']['cpMultiplier']

NIVELES = []  # (nivel, cpm) de 1 a 50 de medio en medio
for n in range(1, 51):
    NIVELES.append(cpm[n - 1])
    if n < 50:
        NIVELES.append(math.sqrt((cpm[n - 1] ** 2 + cpm[n] ** 2) / 2))
CPM2 = [c * c for c in NIVELES]

familia_de, dex_de_familia, dex_especiales = {}, defaultdict(set), set()
for s in pokes:
    if s.get('familyId'):
        familia_de.setdefault(s['_dex'], s['familyId'])
        dex_de_familia[s['familyId']].add(s['_dex'])
    if s.get('pokemonClass') in CLASES_ESPECIALES:
        dex_especiales.add(s['_dex'])

# ---------- PvPoke ----------
pv = json.load(open(f'{PVPOKE}/gamemaster.json', encoding='utf-8'))
pv_por_id = {p['speciesId']: p for p in pv['pokemon']}
dex_publicados = {p['dex'] for p in pv['pokemon'] if p.get('released')}
pv_familias = defaultdict(set)
for p in pv['pokemon']:
    if (p.get('family') or {}).get('id'):
        pv_familias[p['family']['id']].add(p['dex'])


def familia(dex):
    if dex in familia_de:
        return tuple(sorted(dex_de_familia[familia_de[dex]]))
    for ds in pv_familias.values():  # especies más nuevas que el game master
        if dex in ds:
            return tuple(sorted(ds))
    return (dex,)


familias, indice_familia = [], {}


def id_familia(dex):
    f = familia(dex)
    if f not in indice_familia:
        indice_familia[f] = len(familias)
        familias.append(list(f))
    return indice_familia[f]


def banda(iv):
    return 0 if iv == 0 else 1 if iv <= 5 else 2 if iv <= 10 else 3 if iv <= 14 else 4


def tabla_pvp(atk, dfn, ps, tope):
    """Por cada banda (a, d, ps) -> mejor % (por mil) del producto de estadísticas respecto al rango 1."""
    sp = {}
    for a in range(16):
        for d in range(16):
            for s in range(16):
                k = (atk + a) * math.sqrt(dfn + d) * math.sqrt(ps + s) / 10
                if tope is None:
                    i = len(NIVELES) - 1
                else:  # PC = floor(k * cpm^2) <= tope  <=>  cpm^2 < (tope + 1) / k
                    i = bisect.bisect_left(CPM2, (tope + 1) / k) - 1
                    if i < 0:
                        continue
                c = NIVELES[i]
                sp[(a, d, s)] = (atk + a) * c * (dfn + d) * c * max(10, math.floor((ps + s) * c))
    top = max(sp.values())
    out = {}
    for (a, d, s), v in sp.items():
        clave = banda(a) * 25 + banda(d) * 5 + banda(s)
        out[clave] = max(out.get(clave, 0), math.floor(v / top * 1000))
    return out


tablas = {}
entradas = {}  # (liga, familia) -> entrada
ligas_out = []
for lid, nombre, fichero, tope in LIGAS:
    ranking = json.load(open(f'{PVPOKE}/rankings/{fichero}', encoding='utf-8'))
    lista = []
    for rango, e in enumerate(ranking[:TOP_MAX_PVP], start=1):
        p = pv_por_id.get(e['speciesId'])
        if not p:
            continue
        # Los legendarios van marcados: la papelera ya los protege con !legendario, etc.,
        # pero la búsqueda del meta los ofrece.
        legendaria = all(d in dex_especiales for d in familia(p['dex']))
        bs = p['baseStats']
        clave = (bs['atk'], bs['def'], bs['hp'], tope)
        if clave not in tablas:
            tablas[clave] = tabla_pvp(bs['atk'], bs['def'], bs['hp'], tope)
        fi = id_familia(p['dex'])
        ent = entradas.get((lid, fi))
        if ent is None:
            ent = entradas[(lid, fi)] = {'r': rango, 'f': fi, 'n': [], '_t': {}}
            if legendaria:
                ent['l'] = 1
            lista.append(ent)
        ent['n'].append(p['speciesName'])
        for k, v in tablas[clave].items():
            ent['_t'][k] = max(ent['_t'].get(k, 0), v)
    for ent in lista:
        ent['t'] = [x for k, v in sorted(ent.pop('_t').items()) if v >= PM_MINIMO for x in (k, v)]
    ligas_out.append({'id': lid, 'nombre': nombre, 'pc': tope, 'ranking': lista})

# ---------- atacantes de incursión por tipo ----------


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
    if dex not in dex_publicados or not (s.get('stats') or {}).get('baseAttack'):
        continue
    variantes = [(s['stats'], {s.get('type'), s.get('type2')}, s.get('form') or s.get('pokemonId'))]
    for o in s.get('tempEvoOverrides') or []:
        if o.get('stats') and o.get('tempEvoId'):
            variantes.append((o['stats'], {o.get('typeOverride1'), o.get('typeOverride2')},
                              f"{o['tempEvoId'].replace('TEMP_EVOLUTION_', '')} {s.get('pokemonId')}"))
    rapidos, cargados = ataques(s, True), ataques(s, False)
    for stats, tipos, nombre in variantes:
        if 'ETERNAMAX' in str(nombre):  # solo existe en combates Max, no se puede usar en incursiones
            continue
        for t in TIPOS:
            pt = f'POKEMON_TYPE_{t}'
            mejor = max((rating(stats, tipos, f, c) or 0 for f in rapidos if f['pokemonType'] == pt
                         for c in cargados if c['pokemonType'] == pt), default=0)
            if mejor:
                puntuaciones[t].append((mejor, bonito(nombre), dex))

tipos_out = []
for t, nombre_tipo in TIPOS.items():
    vistas, top, normales = set(), [], 0
    for _, nombre, dex in sorted(puntuaciones[t], key=lambda x: (-x[0], len(x[1]))):  # empate: forma normal
        fi = id_familia(dex)
        if fi in vistas:
            continue
        vistas.add(fi)
        # Los legendarios van marcados: la papelera ya los protege, pero la búsqueda de atacantes los ofrece.
        legendario = dex in dex_especiales
        top.append({'n': nombre, 'f': fi, 'l': 1} if legendario else {'n': nombre, 'f': fi})
        normales += not legendario
        if normales == TOP_MAX_ATACANTES:
            break
    tipos_out.append({'id': t.lower(), 'nombre': nombre_tipo, 'top': top})

# ---------- especies para "siempre guardar" ----------
especies, vistas = [], set()
for p in sorted(pv['pokemon'], key=lambda p: (p['dex'], p['speciesId'])):
    sid = p['speciesId']
    if not p.get('released') or re.search(r'_(shadow|mega|mega_x|mega_y|primal|xs|xl)$', sid) or sid in vistas:
        continue
    vistas.add(sid)
    especies.append([sid, p['speciesName'], p['dex'], id_familia(p['dex'])])

# ---------- salida ----------
ahora = dt.datetime.now(dt.timezone.utc)
datos_juego = None
if GM_TS and os.path.exists(GM_TS):
    try:
        datos_juego = dt.datetime.fromtimestamp(int(open(GM_TS).read().strip()) / 1000, dt.timezone.utc)
    except ValueError:
        pass
datos = {
    'generada': ahora.isoformat(timespec='minutes'),
    'datos_juego': datos_juego.date().isoformat() if datos_juego else None,
    'config': json.load(open(os.path.join(AQUI, 'config.json'), encoding='utf-8')),
    'familias': familias,
    'ligas': ligas_out,
    'tipos': tipos_out,
    'especies': especies,
}
os.makedirs(SALIDA, exist_ok=True)
texto = json.dumps(datos, ensure_ascii=False, separators=(',', ':'))
open(os.path.join(SALIDA, 'datos.json'), 'w', encoding='utf-8').write(texto)

plantilla = open(os.path.join(AQUI, 'web', 'plantilla.html'), encoding='utf-8').read()
motor = open(os.path.join(AQUI, 'web', 'papelera.js'), encoding='utf-8').read()
pagina = (plantilla.replace('/*__PAPELERA_JS__*/', motor)
          .replace('"__DATOS__"', texto.replace('</', '<\\/')))
open(os.path.join(SALIDA, 'index.html'), 'w', encoding='utf-8').write(pagina)
shutil.copytree(os.path.join(AQUI, 'web', 'estaticos'), SALIDA, dirs_exist_ok=True)  # fuentes e icono
print(f'OK · {len(ligas_out)} ligas · {sum(len(l["ranking"]) for l in ligas_out)} entradas PvP · '
      f'{len(familias)} familias · datos.json {len(texto) // 1024} KB')
