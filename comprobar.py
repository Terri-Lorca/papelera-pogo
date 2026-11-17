#!/usr/bin/env python3
"""Comprueba la cadena generada simulando el buscador de Pokémon GO. Si algo falla, no se publica."""
import json
import os
import re
import sys

R = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'docs', 'papelera.json'), encoding='utf-8'))
cadena = R['cadena']


def banda(iv):
    return 0 if iv == 0 else 1 if iv <= 5 else 2 if iv <= 10 else 3 if iv <= 14 else 4


def estrellas(a, d, h):
    p = (a + d + h) / 45
    return 4 if p == 1 else 3 if p >= 0.8 else 2 if p >= 0.6667 else 1 if p >= 0.5 else 0


def cumple(t, pk):
    neg = t.startswith('!')
    t = t[1:] if neg else t
    if t == '#':
        r = pk.get('etiqueta', False)
    elif re.fullmatch(r'[0-4]\*', t):
        r = estrellas(*pk['iv']) == int(t[0])
    elif m := re.fullmatch(r'(\d)-(\d)(ataque|defensa|PS)', t):
        r = int(m.group(1)) <= banda(pk['iv'][{'ataque': 0, 'defensa': 1, 'PS': 2}[m.group(3)]]) <= int(m.group(2))
    elif m := re.fullmatch(r'(\d+)-(\d+)', t):
        r = int(m.group(1)) <= pk['dex'] <= int(m.group(2))
    elif re.fullmatch(r'\d+', t):
        r = pk['dex'] == int(t)
    else:
        r = t in pk.get('marcas', ())
    return r != neg


def papelera(pk):
    return all(any(cumple(t, pk) for t in c.split(',')) for c in cadena.split('&'))


pvp = R['pvp_guardar'][len(R['pvp_guardar']) // 2]
atk = R['solo_atacantes'][len(R['solo_atacantes']) // 2]
libre = next(d for d in range(10, 1000) if d not in R['pvp_guardar'] and d not in R['solo_atacantes'])
casos = [
    ('sin espacios', ' ' not in cadena),
    ('longitud razonable', 300 < len(cadena) < 6000),
    ('suficientes familias PvP', len(R['pvp_guardar']) >= 40),
    ('suficientes atacantes', len(R['solo_atacantes']) >= 40),
    ('meta PvP con IV bajos se queda', not papelera(dict(dex=pvp, iv=(0, 3, 15)))),
    ('atacante con ataque alto se queda', not papelera(dict(dex=atk, iv=(13, 2, 2)))),
    ('atacante con ataque bajo se va', papelera(dict(dex=atk, iv=(4, 6, 6)))),
    ('Pokémon cualquiera de 0 estrellas se va', papelera(dict(dex=libre, iv=(1, 2, 3)))),
    ('100 % se queda', not papelera(dict(dex=libre, iv=(15, 15, 15)))),
    ('variocolor se queda', not papelera(dict(dex=libre, iv=(1, 2, 3), marcas={'variocolor'}))),
    ('legendario se queda', not papelera(dict(dex=libre, iv=(1, 2, 3), marcas={'legendario'}))),
    ('etiquetado se queda', not papelera(dict(dex=libre, iv=(1, 2, 3), etiqueta=True))),
]
fallos = [n for n, ok in casos if not ok]
for n, ok in casos:
    print('OK ' if ok else 'MAL', n)
sys.exit(1 if fallos else 0)
