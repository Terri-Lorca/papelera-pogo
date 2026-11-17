# Papelera Pokémon GO

Genera cada día una cadena de búsqueda para transferir en masa lo que no te sirve. La publica en una página con botón **Copiar** y en un `cadena.txt` que puedes copiar con un Atajo del iPhone.

La cadena deja fuera:
- **Meta PvP:** familias completas (con preevoluciones) del top de PvPoke en la liga de 500 PC, la Super Ball, la Ultra Ball y la Master Ball.
- **Atacantes de incursión:** las familias de los 10 mejores de cada tipo (incluidas megas), solo los ejemplares con 11–15 de ataque.
- **Especiales:** variocolor, oscuros, legendarios, singulares, ultraentes, con disfraz o fondo, dinamax, gigamax, con ataques especiales, intercambiados y todo lo etiquetado.
- **Los de 4 estrellas.**

Está pensada para el juego en español. Los datos salen de PvPoke y del game master del juego (PokeMiners), los dos en GitHub.

## Ponerla en marcha (una vez, desde el ordenador)

1. Crea en GitHub un repositorio **público** vacío, por ejemplo `papelera-pogo`.
2. Desde esta carpeta:
   ```bash
   git init && git add . && git commit -m "Papelera Pokémon GO"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/papelera-pogo.git
   git push -u origin main
   ```
3. En el repo, **Settings → Pages**: *Source* = **Deploy from a branch**, rama **main**, carpeta **/docs** → **Save**.
   La página quedará en `https://TU_USUARIO.github.io/papelera-pogo/`.
4. En **Actions → Papelera Pokémon GO → Run workflow** lánzala una vez para comprobar que va.
   A partir de ahí se regenera sola todos los días hacia las 06:17 (hora de España en invierno).

Si el paso *Publicar* falla con un error de permisos: **Settings → Actions → General → Workflow permissions → Read and write permissions**.

## Copiarla con un toque desde el iPhone

App **Atajos** → **+** → añade estas acciones:
1. **Obtener contenido de URL** → `https://TU_USUARIO.github.io/papelera-pogo/cadena.txt`
2. **Copiar al portapapeles**
3. (Opcional) **Mostrar notificación** → "Cadena copiada"

Ponle de nombre "Papelera PoGo" y añádelo a la pantalla de inicio. Lo tocas, abres el juego y pegas.

## Personalizar

Edita `config.json` y haz commit. El cambio se aplica en la siguiente ejecución, o al momento con *Run workflow*.

| Campo | Qué hace |
|---|---|
| `top_pvp` | Cuántos Pokémon del ranking de cada liga se protegen. |
| `top_atacantes_por_tipo` | Cuántas familias de atacantes por tipo. |
| `siempre_guardar` | Especies que quieres guardar siempre, con su nombre en PvPoke (inglés): `"skwovet"`, `"stunfisk_galarian"`… |
| `estrellas_papelera` | `"0*,1*,2*,3*"` por defecto. Pon `"0*,1*,2*"` para ser más conservador. |

## Detalles

- Antes de publicar, `comprobar.py` simula el buscador del juego con varios casos de prueba. Si algo falla (por ejemplo, porque cambia el formato de los datos), no se publica nada y la página se queda con la última cadena buena.
- Los atacantes se ordenan con un estimador de DPS/TDO a nivel 40 con 15/15/15, contra un rival genérico débil a ese tipo.
- Como la página cambia cada día, el workflow hace un commit diario. Eso evita que GitHub desactive la tarea programada por inactividad.
- Los datos de incursiones dependen de cuándo actualice PokeMiners el game master. La fecha aparece en la página.
