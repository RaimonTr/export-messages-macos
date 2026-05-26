# exportar-imessages-macos

Script interactivo para exportar conversaciones de Mensajes/iMessage en macOS a un HTML imprimible, incluyendo texto e imágenes adjuntas cuando están disponibles localmente.

## Qué hace

- Lee la base local de Mensajes de macOS: "~/Library/Messages/chat.db"
- Lista las conversaciones disponibles.
- Permite elegir una conversación por número.
- Exporta los mensajes ordenados cronológicamente.
- Extrae texto desde "message.text" cuando existe.
- Si "message.text" está vacío, decodifica `message.attributedBody` con Swift para conservar acentos y caracteres UTF-8.
- Copia imágenes/adjuntos a una carpeta junto al HTML.
- Genera un HTML que puede imprimirse o guardarse como PDF desde el navegador.

## Qué NO hace

- No modifica "chat.db".
- No borra mensajes.
- No borra adjuntos.
- No sube datos a Internet.
- No requiere credenciales.
- No usa servicios externos.

## Requisitos

macOS con:

- Python 3
- SQLite disponible en el sistema
- Swift disponible en el sistema
- La conversación sincronizada localmente en la app Mensajes/iMessage
- Acceso total al disco para la app de terminal usada

Si aparece un error de permisos al abrir "chat.db", hay que dar Acceso total al disco a Terminal, iTerm u otra app de terminal:

"Ajustes del Sistema > Privacidad y seguridad > Acceso total al disco". Buscas la app que corresponda y la activas.

## Uso

Ejecutar: "python3 exportar_imessages.py"

El script listará las conversaciones disponibles y preguntará cuál exportar.

Al terminar generará archivos en "~/Downloads", por ejemplo:

iMessages_Apple_YYYYMMDD_HHMMSS.html
iMessages_Apple_YYYYMMDD_HHMMSS_imagenes/
iMessages_Apple_YYYYMMDD_HHMMSS_tmp/

Para crear el PDF:

1. Abrir el HTML generado.
2. Ir a "Archivo > Imprimir".
3. Elegir "PDF > Guardar como PDF".

## Privacidad

El script se ejecuta localmente. La conversación exportada puede contener datos personales, teléfonos, imágenes, direcciones, números de seguimiento u otra información sensible. Revisa el HTML/PDF antes de compartirlo.

## Limitaciones

- Solo exporta lo que esté disponible localmente en el Mac.
- Si Mensajes no ha descargado todo el historial o ciertos adjuntos, esos elementos pueden faltar.
- Algunos adjuntos que no sean imagen pueden copiarse como archivo, pero no se incrustan visualmente en el HTML.
- El formato generado es práctico para lectura e impresión, no una réplica exacta de la interfaz de Mensajes.

## Licencia

MIT.
