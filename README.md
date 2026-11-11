# Scoreboard27 — marcador nativo para FIFA16

Prueba experimental **v0.1**: gráficos de FC27 con el reloj y el resultado manejados por FIFA16, sin `fc27overlay.asi`.

[**Descargar el ZIP de prueba**](https://github.com/pochoct02-png/Scoreboard27/raw/refs/heads/main/fc27_nativo_v01_prueba.zip)

## Estado

Validado fuera del juego con un intérprete APT: inicialización, reloj hasta 120 minutos, cambios de resultado, tiempo añadido, contadores de expulsiones y entrada/salida. **Falta probar la carga en FIFA16 y medir los FPS.**

Esta versión conserva el fundido de FIFA16. Las animaciones completas de FC27, su intro y sus formaciones siguen pendientes. Los archivos 9018 y 9042 incluidos restauran las pantallas del pack anterior para poder desactivar el plugin.

## Instalación

1. Cerrá FIFA16 y hacé una copia de tu pack de Champions.
2. Descomprimí el ZIP. Copiá `game/` y `fonts/` de `FC27_NATIVO_v01/` sobre esas carpetas del pack de prueba.
3. Conservá sus archivos `globalcomponents`. Revisá que `fonts/fonts.txt` incluya `Champions Regular.ttf` y `Champions.ttf`.
4. Mové solamente `Mods/fc27overlay.asi` fuera de `Mods` mientras probás. Conservá el resto del cargador y ReShade.
5. Seleccioná el pack con tu server habitual.

Leé **LEEME.txt dentro del ZIP** para las instrucciones completas y la reversión.

SHA-256 del ZIP:
`6064a1333f013d87327fd6f2533ada256a53b7a995b865bb3e3d4c50111277ab`
