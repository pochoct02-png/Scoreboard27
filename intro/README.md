# Intro FC27 para FIFA16 — prueba v0.2

La intro anterior todavía usaba el arte del pack de FIFA16. Esta adaptación conecta el FullPanel original de FC27 con los nombres, escudos y estadio recibidos por FIFA16. Conserva las funciones originales de entrada, salida y animación de fondo; la inicialización se limita al cartel previo al partido para evitar los proveedores modernos de jugadores.

**Experimental: falta probar la carga y el renderizado en FIFA16.** La equivalencia visual, la transparencia, la reproducción de la propiedad de animación de fotograma, la escala y los FPS siguen pendientes.

## Estado de entrega

Las fuentes, el verificador y las instrucciones están guardados en esta rama. El paquete se generó y se verificó fuera del juego antes de la interrupción, pero **el ZIP v0.2 no está publicado**: su subida quedó interrumpida y después falló el entorno de ejecución. Los archivos generados no se pudieron recuperar durante esta continuación.

[Instalación y reversión](LEEME_v02.txt) · [Resultados previos de verificación](VERIFICACION_v02.json)

## Reconstruir

Requiere Python 3 y los archivos originales proporcionados para esta adaptación: lib.zip y UEFA - Champions League.zip. Descomprimilos y ejecutá desde la raíz del repositorio:

    python tools/build_intro.py --fc27 /ruta/lib --native "/ruta/UEFA - Champions League" --output work/intro_v02
    python tools/verify_intro.py --fc27 /ruta/lib --output work/intro_v02

El directorio de entrada lib debe contener globalComponents/ y Overlays/. La entrada UEFA - Champions League debe contener game/ y fonts/. No requiere bibliotecas de terceros.

El generador crea la intro 9042 y dos componentes adicionales con nombres propios. Incluye los overlays 9002 y 9018 de v0.1, sin cambios, para probar el conjunto con fc27overlay.asi desactivado, y copias de los tres overlays originales para restaurar. Las formaciones no reciben una adaptación nueva.

El editor APT conserva los offsets originales y agrega tablas y acciones al final. Las sustituciones de los nombres de los componentes mantienen su longitud. La verificación compara el bytecode de las animaciones con el original y ejecuta el adaptador emitido, incluyendo tablas de parámetros y saltos. No ejecuta el motor de FIFA16.

Los resultados registrados corresponden a la ejecución previa al fallo del entorno. Durante la recuperación, las fuentes se guardaron mediante el conector de GitHub; no fue posible repetir las pruebas después de esa publicación.
