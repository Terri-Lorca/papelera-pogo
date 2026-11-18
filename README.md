# Papelera de Pokémon GO

Una página para construir la búsqueda que vacía tu almacenamiento sin perder nada bueno, con un botón para copiarla. Se actualiza sola cada día con el meta de PvP y los mejores atacantes de incursión.

- **Página:** https://terri-lorca.github.io/papelera-pogo/
- **Cadena para el atajo del iPhone:** https://raw.githubusercontent.com/Terri-Lorca/papelera-pogo/main/docs/cadena.txt

## Qué protege

- **Meta PvP:** los Pokémon del top de PvPoke en la liga de 500 PC, la Super Ball, la Ultra Ball y la Master Ball que pueden llegar a un % de su mejor versión en esa liga (el mismo % que da Poke Genie). Por defecto, 95 %.
- **Atacantes de incursión:** las familias de los mejores atacantes de cada tipo, megas incluidas, con 11 o más de ataque. Los legendarios ya van protegidos como especiales.
- **Especiales:** variocolor, oscuros, legendarios, singulares, ultraentes, con disfraz o fondo, dinamax, gigamax, con ataques especiales, intercambiados (incluye los con suerte) y todo lo etiquetado.
- **Siempre guardar:** especies que quieres conservar con cualquier IV.
- **Límites:** solo entran Pokémon de las estrellas que elijas y, si quieres, hasta un PC máximo.

### Hasta dónde llega la precisión

El buscador del juego no ve los IV exactos, solo las barras de la valoración: 0, 1–5, 6–10, 11–14 y 15. Por eso:

- Nunca va a la papelera un Pokémon del meta que pueda llegar al % elegido. `comprobar.py` lo verifica antes de publicar.
- Algunos que no llegan se guardan de más, porque comparten barras con otros que sí. La página te dice cuántos te quedas de cada 100.
- El 95 % es bastante generoso: con él te quedas con unos 79 de cada 100 Pokémon de las familias meta. Con el 98 %, con unos 28.

## Búsquedas rápidas

Debajo de los ajustes hay búsquedas listas para copiar, cada una con sus opciones:

- **Atacantes para incursiones:** por tipo, top 3 a 15, con o sin legendarios y oscuros. Para el IV:
  - *Más de 40 (aprox.):* salen todos los de 41 a 45 y algunos de 37 a 40 con las tres barras en 11 o más.
  - *Más de 40 (seguro):* todos los que salen tienen 41 o más, aunque se escapan algunos (como un 14/14/14).
  - También 3 estrellas, 15 de ataque, solo 100 % o ataque 11+.
- **Meta PvP por liga:** los Pokémon de una liga (o de todas) que pueden llegar a un % mínimo, con o sin legendarios. Para revisarlos y etiquetarlos.
- **Listos para liga**, **Repetidos** (`cantidad`), **Joyas y curiosidades** y **Pueden evolucionar ya**.

El buscador no puede sumar IV, así que "más de 40" exacto no existe: estas dos opciones son lo más cerca que se puede llegar, por arriba y por abajo.

## Ajustes

En la página puedes cambiarlo todo. Los cambios se guardan en tu navegador.

El atajo del iPhone usa `config.json`. Para que use tus ajustes de la página, pulsa **Copiar ajustes para config.json**, abre **Editar config.json** y pega.

| Campo | Qué hace |
|---|---|
| `estrellas_papelera` | Estrellas que pueden ir a la papelera, por ejemplo `[0, 1, 2, 3]`. |
| `pc_maximo` | PC máximo. `null` para no poner límite. |
| `pvp_minimo` | % mínimo para guardar un Pokémon del meta (de 90 a 99). |
| `top_pvp` | Cuántos del ranking de cada liga cuentan como meta. `0` desactiva la liga. |
| `top_atacantes_por_tipo` | Cuántos atacantes de cada tipo. `0` para no protegerlos. |
| `ataque_minimo_atacantes` | `11` (11 a 15 de ataque) o `15`. |
| `siempre_guardar` | Especies con su nombre en PvPoke, por ejemplo `"skwovet"`. |
| `proteger` | Cada especial y extra: `listos_para_liga`, `unicos` (el único de su especie), `nundos`, `tamanos`, `evolucionables`… |

## Cómo funciona

Cada día, hacia las 06:17, GitHub Actions:
1. Descarga los rankings y datos de PvPoke y el game master del juego (PokeMiners).
2. `generar_papelera.py` calcula, para cada Pokémon del meta y cada liga, el % de producto de estadísticas de las 4096 combinaciones de IV, lo resume por barras y ordena los atacantes por tipo. Escribe `docs/datos.json` y la página.
3. `node construir.js` arma la cadena de `config.json` con `web/papelera.js`, el mismo motor que usa la página.
4. `comprobar.py` simula el buscador del juego. Si algo falla, no se publica y se queda la versión anterior.

Para lanzarlo a mano: **Actions → Papelera Pokémon GO → Run workflow**.
