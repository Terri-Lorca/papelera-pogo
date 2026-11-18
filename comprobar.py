#!/usr/bin/env python3
"""Comprueba docs/cadena.txt simulando el buscador de Pokémon GO. Si algo falla, no se publica.

Garantía principal: ningún Pokémon del meta que pueda llegar al % mínimo en una liga elegida
acaba en la papelera, ni ningún atacante con el ataque mínimo.
"""
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
cadena = open(os.path.join(AQUI, 'docs', 'cadena.txt'), encoding='utf-8').read()
datos = json.load(open(os.path.join(AQUI, 'docs', 'datos.json'), encoding='utf-8'))
cfg = json.load(open(os.path.join(AQUI, 'config.json'), encoding='utf-8'))
CLAUSULAS = [c.split(',') for c in cadena.split('&')]
MIN_BANDA = [0, 1, 6, 11, 15]  # valor más bajo de cada banda (el peor caso para las estrellas)


def banda(iv):
    return 0 if iv == 0 else 1 if iv <= 5 else 2 if iv <= 10 else 3 if iv <= 14 else 4


def estrellas(a, d, h):
    p = (a + d + h) / 45
    return 4 if p == 1 else 3 if p >= 0.8 else 2 if p >= 0.6667 else 1 if p >= 0.5 else 0


def rango(txt):
    a, _, b = txt.partition('-')
    return (int(a) if a else 0), (int(b) if b else 10 ** 6) if _ else int(a)


def cumple(t, pk):
    neg = t.startswith('!')
    t = t[1:] if neg else t
    if t == '#':
        r = pk.get('etiqueta', False)
    elif re.fullmatch(r'[0-4]\*', t):
        r = estrellas(*pk['iv']) == int(t[0])
    elif m := re.fullmatch(r'pc(\d*-?\d*)', t):
        lo, hi = rango(m.group(1))
        r = lo <= pk.get('pc', 500) <= hi
    elif m := re.fullmatch(r'(\d)(?:-(\d))?(ataque|defensa|PS)', t):
        lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
        r = lo <= banda(pk['iv'][{'ataque': 0, 'defensa': 1, 'PS': 2}[m.group(3)]]) <= hi
    elif m := re.fullmatch(r'cantidad(\d*-?\d*)', t):
        lo, hi = rango(m.group(1)) if m.group(1) else (2, 10 ** 6)
        r = lo <= pk.get('cantidad', 2) <= hi
    elif re.fullmatch(r'\d+(-\d+)?', t):
        lo, hi = rango(t)
        r = lo <= pk['dex'] <= hi
    else:
        r = t in pk.get('marcas', ())
    return r != neg


def papelera(pk):
    return all(any(cumple(t, pk) for t in c) for c in CLAUSULAS)


fallos = []


def check(nombre, ok):
    print('OK ' if ok else 'MAL', nombre)
    if not ok:
        fallos.append(nombre)


# 1) Meta PvP: las bandas que llegan al mínimo nunca van a la papelera.
T = round(cfg.get('pvp_minimo', 95) * 10)
buenas = {}
for liga in datos['ligas']:
    top = cfg['top_pvp'].get(liga['id'], 0)
    for e in liga['ranking']:
        if e['r'] <= top and not e.get('l'):  # los legendarios los protege !legendario
            t = e['t']
            buenas.setdefault(e['f'], set()).update(t[i] for i in range(0, len(t), 2) if t[i + 1] >= T)
malas, total_fuera, en_papelera = [], 0, 0
for f, bandas in buenas.items():
    dex = datos['familias'][f][0]
    for k in range(125):
        iv = (MIN_BANDA[k // 25], MIN_BANDA[k // 5 % 5], MIN_BANDA[k % 5])
        va = papelera({'dex': dex, 'iv': iv})
        if k in bandas and va:
            malas.append((dex, iv))
        elif k not in bandas:
            total_fuera += 1
            en_papelera += va
check(f'ningún Pokémon del meta que llegue al {T / 10:g} % va a la papelera ({len(buenas)} familias)', not malas)
check(f'el filtro PvP sí quita algo ({en_papelera} de {total_fuera} bandas flojas van a la papelera)', en_papelera > 0)

# 2) Atacantes de incursión: con el ataque mínimo se quedan.
amin = cfg.get('ataque_minimo_atacantes', 11)
n = cfg.get('top_atacantes_por_tipo', 0)
if n and amin:
    fams = {a['f'] for t in datos['tipos'] for a in [x for x in t['top'] if not x.get('l')][:n]}
    malos = [f for f in fams if papelera({'dex': datos['familias'][f][0], 'iv': (amin, 1, 1)})]
    check(f'ningún atacante con {amin}+ de ataque va a la papelera ({len(fams)} familias)', not malos)

# 3) Lo básico.
meta_o_atk = set()
for f in buenas:
    meta_o_atk.update(datos['familias'][f])
if n and amin:
    for f in fams:
        meta_o_atk.update(datos['familias'][f])
libre = next(d for d in range(10, 1000) if d not in meta_o_atk)
check('sin espacios', ' ' not in cadena)
check('un Pokémon cualquiera de 0 estrellas va a la papelera', papelera({'dex': libre, 'iv': (1, 2, 3)}))
check('los 100 % se quedan', not papelera({'dex': libre, 'iv': (15, 15, 15)}))
for marca in ('variocolor', 'oscuro', 'legendario', 'singular', 'disfraz'):
    check(f'{marca}: se queda', not papelera({'dex': libre, 'iv': (1, 2, 3), 'marcas': {marca}}))
check('los etiquetados se quedan', not papelera({'dex': libre, 'iv': (1, 2, 3), 'etiqueta': True}))
if cfg.get('pc_maximo'):
    check(f"los de más de {cfg['pc_maximo']} PC se quedan",
          not papelera({'dex': libre, 'iv': (1, 2, 3), 'pc': cfg['pc_maximo'] + 1}))
if cfg.get('proteger', {}).get('unicos'):
    check('el único de su especie se queda', not papelera({'dex': libre, 'iv': (1, 2, 3), 'cantidad': 1}))
porid = {e[0]: e for e in datos['especies']}
for sid in cfg.get('siempre_guardar', []):
    if sid in porid:
        check(f'{porid[sid][1]} se queda siempre', not papelera({'dex': porid[sid][2], 'iv': (1, 2, 3)}))
sys.exit(1 if fallos else 0)
