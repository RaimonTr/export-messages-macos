# export-messages-macos

Script interactivo para exportar conversaciones de Mensajes/Messages en macOS a un HTML imprimible, incluyendo texto e imágenes adjuntas cuando estén disponibles localmente.

## Antes de empezar

Para forzar a Mensajes a que descargue una conversación entera (o lo máximo que pueda recuperar), navega al inicio de la conversación, al primer mensaje de todos. Con esto conseguirás que se descarguen localmente los archivos.

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
- SQLite
- Swift
- La conversación sincronizada localmente en la app Mensajes/Messages
- Acceso total al disco para la app de terminal utilizada

En la mayoría de instalaciones de macOS, SQLite ya está disponible.

Python 3 y Swift pueden estar ya disponibles según la configuración del sistema. Puedes comprobarlo con:

`python3 --version`

`sqlite3 --version`

`swift --version`

Si falta `python3`, puedes instalarlo, por ejemplo, con Homebrew:

`brew install python`

Si falta `swift`, instala las herramientas de línea de comandos de Apple:

`xcode-select --install`

Si aparece un error de permisos al abrir `chat.db`, hay que dar Acceso total al disco a Terminal, iTerm u otra app de terminal que estés usando:

`Ajustes del Sistema > Privacidad y seguridad > Acceso total al disco`

Busca la app correspondiente y actívala.
## Uso

Para ejecutarlo, en la Terminal: ```python3 export-messages-macos.py```

El script listará las conversaciones disponibles y preguntará cuál exportar.

Al terminar creará los archivos en la carpeta Descargas (`~/Downloads` en Terminal), por ejemplo:

iMessages_Apple_YYYYMMDD_HHMMSS.html

iMessages_Apple_YYYYMMDD_HHMMSS_imagenes/

iMessages_Apple_YYYYMMDD_HHMMSS_tmp/

Para crear el PDF:

1. Abrir el HTML generado.
2. Ir a "Archivo > Imprimir".
3. Elegir "PDF > Guardar como PDF".

## Privacidad

El script se ejecuta de forma local en tu ordenador. La conversación exportada puede contener datos personales, teléfonos, imágenes, direcciones, números de seguimiento u otra información sensible. Revisa el HTML/PDF antes de compartirlo.

## Limitaciones

- Sólo exporta lo que esté disponible localmente en el Mac.
- Si Mensajes no ha descargado todo el historial o ciertos adjuntos, esos elementos pueden faltar. Asegúrate de ir al inicio de la conversación que quieres exportar para forzar a Mensajes a que descargue todo. 
- Algunos adjuntos que no sean imagen pueden copiarse como archivo, pero no se incrustan visualmente en el HTML.
- El formato generado es práctico para lectura e impresión, no una réplica exacta de la interfaz de Mensajes.

## Licencia

MIT.
