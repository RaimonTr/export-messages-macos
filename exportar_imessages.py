#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Exportador interactivo de conversaciones de Mensajes/iMessage en macOS a HTML imprimible.

- Primero intenta usar message.text.
- Si message.text está vacío, decodifica message.attributedBody usando Swift para conservar UTF-8 y acentos.
- Copia imágenes/adjuntos a una carpeta junto al HTML y usa rutas relativas.
- No modifica chat.db.
- No borra nada.
- Crea archivos nuevos en ~/Downloads.
"""

from __future__ import annotations

import html
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


HOME = Path.home()
CHAT_DB = HOME / "Library" / "Messages" / "chat.db"
DOWNLOADS = HOME / "Downloads"


@dataclass
class Chat:
    rowid: int
    last_message_date: str
    display_name: str
    chat_identifier: str
    message_count: int


@dataclass
class Message:
    rowid: int
    date: str
    who: str
    css_class: str
    text: Optional[str]


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "[S/n]" if default else "[s/N]"
    while True:
        value = input(f"{prompt} {suffix}: ").strip().lower()
        if not value:
            return default
        if value in {"s", "si", "sí", "y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Responde s/n.")


def check_requirements() -> None:
    if not CHAT_DB.exists():
        die("No existe la base de Mensajes esperada en ~/Library/Messages/chat.db")

    try:
        subprocess.run(["swift", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        die("No encuentro 'swift'. En macOS suele estar disponible con Xcode Command Line Tools.")

    try:
        con = sqlite3.connect(f"file:{CHAT_DB}?mode=ro", uri=True)
        con.execute("SELECT 1").fetchone()
        con.close()
    except sqlite3.OperationalError as exc:
        die(
            "No puedo abrir ~/Library/Messages/chat.db. Casi seguro falta Acceso total al disco "
            "para la app de terminal que estás usando. Detalle técnico: "
            f"{exc}"
        )


def apple_datetime_expr(column: str) -> str:
    return f"datetime({column}/1000000000 + strftime('%s','2001-01-01'), 'unixepoch', 'localtime')"


def list_chats(limit: int = 80) -> list[Chat]:
    con = sqlite3.connect(f"file:{CHAT_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    sql = f"""
    SELECT
      chat.ROWID AS rowid,
      COALESCE({apple_datetime_expr('MAX(message.date)')}, '') AS last_message_date,
      COALESCE(chat.display_name, '') AS display_name,
      COALESCE(chat.chat_identifier, '') AS chat_identifier,
      COUNT(message.ROWID) AS message_count
    FROM chat
    LEFT JOIN chat_message_join cmj ON cmj.chat_id = chat.ROWID
    LEFT JOIN message ON message.ROWID = cmj.message_id
    GROUP BY chat.ROWID
    ORDER BY MAX(message.date) DESC
    LIMIT ?;
    """

    rows = con.execute(sql, (limit,)).fetchall()
    con.close()

    return [
        Chat(
            rowid=int(r["rowid"]),
            last_message_date=r["last_message_date"],
            display_name=r["display_name"],
            chat_identifier=r["chat_identifier"],
            message_count=int(r["message_count"]),
        )
        for r in rows
    ]


def choose_chat(chats: list[Chat]) -> Chat:
    if not chats:
        die("No se han encontrado conversaciones.")

    print("\nConversaciones encontradas:\n")
    for i, c in enumerate(chats, start=1):
        name = c.display_name or c.chat_identifier or "(sin nombre)"
        print(f"{i:>2}. {c.last_message_date} | {c.message_count:>4} mensajes | {name}")

    while True:
        value = input("\nElige número de conversación a exportar: ").strip()
        if value.isdigit():
            idx = int(value)
            if 1 <= idx <= len(chats):
                chosen = chats[idx - 1]
                print()
                print("Seleccionada:")
                print(f"  ROWID interno: {chosen.rowid}")
                print(f"  Nombre: {chosen.display_name or '(sin nombre)'}")
                print(f"  Identificador: {chosen.chat_identifier or '(sin identificador)'}")
                print(f"  Mensajes: {chosen.message_count}")
                if ask_yes_no("¿Exportar esta conversación?", default=True):
                    return chosen
        print("Número no válido.")


def create_swift_decoder(path: Path) -> None:
    path.write_text(
        """import Foundation

let path = CommandLine.arguments[1]
let data = try Data(contentsOf: URL(fileURLWithPath: path))

if let attr = try? NSKeyedUnarchiver.unarchivedObject(ofClass: NSAttributedString.self, from: data) {
    print(attr.string)
    exit(0)
}

if let attr = NSUnarchiver.unarchiveObject(with: data) as? NSAttributedString {
    print(attr.string)
    exit(0)
}

exit(1)
""",
        encoding="utf-8",
    )


def decode_attributed_body(swift_script: Path, bin_path: Path) -> Optional[str]:
    result = subprocess.run(
        ["swift", str(swift_script), str(bin_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    )
    if result.returncode == 0:
        return result.stdout.rstrip("\n")
    return None


def get_messages(chat_rowid: int) -> list[Message]:
    con = sqlite3.connect(f"file:{CHAT_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    sql = f"""
    SELECT
      message.ROWID AS rowid,
      {apple_datetime_expr('message.date')} AS date,
      CASE WHEN message.is_from_me = 1 THEN 'YO' ELSE 'OTRO' END AS who,
      CASE WHEN message.is_from_me = 1 THEN 'me' ELSE 'them' END AS css_class,
      message.text AS text
    FROM message
    JOIN chat_message_join cmj ON cmj.message_id = message.ROWID
    WHERE cmj.chat_id = ?
    ORDER BY message.date ASC;
    """

    rows = con.execute(sql, (chat_rowid,)).fetchall()
    con.close()

    return [
        Message(
            rowid=int(r["rowid"]),
            date=r["date"],
            who=r["who"],
            css_class=r["css_class"],
            text=r["text"],
        )
        for r in rows
    ]


def write_attributed_body_to_file(message_rowid: int, bin_path: Path) -> bool:
    con = sqlite3.connect(f"file:{CHAT_DB}?mode=ro", uri=True)
    try:
        row = con.execute(
            "SELECT attributedBody FROM message WHERE ROWID = ?;",
            (message_rowid,),
        ).fetchone()
    finally:
        con.close()

    if not row or row[0] is None:
        return False

    bin_path.write_bytes(row[0])
    return True


def get_message_body(msg: Message, swift_script: Path, work_dir: Path) -> str:
    if msg.text and msg.text.strip():
        return msg.text

    bin_path = work_dir / f"{msg.rowid}.bin"
    if write_attributed_body_to_file(msg.rowid, bin_path):
        decoded = decode_attributed_body(swift_script, bin_path)
        if decoded and decoded.strip():
            return decoded

    return "[mensaje sin texto extraíble o adjunto]"


def get_attachments(message_rowid: int) -> list[sqlite3.Row]:
    con = sqlite3.connect(f"file:{CHAT_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    sql = """
    SELECT
      COALESCE(attachment.filename, '') AS filename,
      COALESCE(attachment.mime_type, '') AS mime_type,
      COALESCE(attachment.transfer_name, '') AS transfer_name,
      COALESCE(attachment.total_bytes, 0) AS total_bytes
    FROM message_attachment_join maj
    JOIN attachment ON attachment.ROWID = maj.attachment_id
    WHERE maj.message_id = ?
    ORDER BY attachment.ROWID ASC;
    """

    rows = con.execute(sql, (message_rowid,)).fetchall()
    con.close()
    return rows


def expand_message_path(filename: str) -> Path:
    if filename.startswith("~/"):
        return HOME / filename[2:]
    return Path(filename).expanduser()


def safe_filename(name: str, fallback: str) -> str:
    raw = name or fallback
    keep = []
    for ch in raw:
        if ch.isalnum() or ch in {".", "_", "-", " "}:
            keep.append(ch)
        else:
            keep.append("_")
    cleaned = "".join(keep).strip()
    return cleaned or fallback


def html_header(title: str, notice: str) -> str:
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
  max-width: 900px;
  margin: 40px auto;
  padding: 0 24px;
  background: #ffffff;
  color: #111111;
}}
h1 {{
  font-size: 22px;
  margin-bottom: 4px;
}}
.notice {{
  font-size: 12px;
  color: #555555;
  margin-bottom: 24px;
}}
.msg {{
  max-width: 78%;
  margin: 10px 0;
  padding: 10px 12px;
  border-radius: 12px;
  page-break-inside: avoid;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}}
.me {{
  margin-left: auto;
  background: #dceeff;
  border: 1px solid #b8d8ff;
}}
.them {{
  margin-right: auto;
  background: #f1f1f1;
  border: 1px solid #dddddd;
}}
.meta {{
  font-size: 11px;
  color: #666666;
  margin-bottom: 5px;
}}
.body {{
  font-size: 14px;
  line-height: 1.35;
}}
.attachments {{
  margin-top: 10px;
}}
.attachments img {{
  display: block;
  max-width: 100%;
  max-height: 620px;
  margin-top: 8px;
  border-radius: 10px;
  border: 1px solid #cccccc;
}}
.attachment-note {{
  font-size: 12px;
  color: #555555;
  margin-top: 8px;
  padding: 6px 8px;
  border: 1px dashed #aaaaaa;
  border-radius: 8px;
  background: #fafafa;
}}
@media print {{
  body {{
    margin: 0;
    max-width: none;
  }}
  .msg {{
    page-break-inside: avoid;
  }}
  .attachments img {{
    max-height: 520px;
  }}
}}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<div class="notice">{html.escape(notice)}</div>
"""


def export_chat(chat: Chat) -> tuple[Path, Path, Path, dict[str, int]]:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    visible_name = chat.display_name or chat.chat_identifier or f"chat_{chat.rowid}"
    base_name = safe_filename(f"iMessages_{visible_name}_{stamp}", f"iMessages_chat_{chat.rowid}_{stamp}")

    base = DOWNLOADS / base_name
    out_html = base.with_suffix(".html")
    img_dir = DOWNLOADS / f"{base_name}_imagenes"
    work_dir = DOWNLOADS / f"{base_name}_tmp"

    img_dir.mkdir(parents=True, exist_ok=False)
    work_dir.mkdir(parents=True, exist_ok=False)

    swift_script = work_dir / "decode_imessage_attr.swift"
    create_swift_decoder(swift_script)

    messages = get_messages(chat.rowid)
    if not messages:
        die("La conversación seleccionada no tiene mensajes.")

    title = f"Conversación iMessage — {visible_name}"
    notice = (
        "Exportación local desde la base de datos de Mensajes de macOS. "
        "Mensajes ordenados cronológicamente. "
        "Texto extraído desde message.text cuando existe; si no existe, desde attributedBody decodificado con Swift. "
        "Las imágenes han sido copiadas a una carpeta local junto al HTML."
    )

    stats = {
        "messages": 0,
        "attachments": 0,
        "images": 0,
        "missing_attachments": 0,
        "message_text_used": 0,
        "attributed_body_used": 0,
    }

    with out_html.open("w", encoding="utf-8") as f:
        f.write(html_header(title, notice))

        for msg in messages:
            stats["messages"] += 1
            used_text_directly = bool(msg.text and msg.text.strip())
            if used_text_directly:
                stats["message_text_used"] += 1
            else:
                stats["attributed_body_used"] += 1

            body_text = get_message_body(msg, swift_script, work_dir)

            f.write(
                f'<div class="msg {html.escape(msg.css_class)}">'
                f'<div class="meta">{html.escape(msg.date)} · {html.escape(msg.who)} · ROWID {msg.rowid}</div>'
                f'<div class="body">{html.escape(body_text)}</div>'
            )

            attachments = get_attachments(msg.rowid)
            if attachments:
                f.write('<div class="attachments">')

                for idx, att in enumerate(attachments, start=1):
                    stats["attachments"] += 1

                    filename = att["filename"]
                    mime = att["mime_type"]
                    transfer = att["transfer_name"] or Path(filename).name or f"adjunto_{idx}"
                    total_bytes = att["total_bytes"]

                    real_path = expand_message_path(filename)
                    copied_name = safe_filename(f"{msg.rowid}_{idx}_{transfer}", f"{msg.rowid}_{idx}_adjunto")
                    dest = img_dir / copied_name
                    rel = f"{img_dir.name}/{copied_name}"

                    if real_path.exists() and real_path.is_file():
                        shutil.copy2(real_path, dest)

                        if mime.startswith("image/"):
                            stats["images"] += 1
                            f.write(f'<img src="{html.escape(rel)}" alt="{html.escape(transfer)}">')
                        else:
                            f.write(
                                '<div class="attachment-note">'
                                f'Adjunto no imagen copiado: {html.escape(transfer)} · '
                                f'{html.escape(mime or "sin MIME")} · {html.escape(str(total_bytes))} bytes<br>'
                                f'{html.escape(rel)}'
                                '</div>'
                            )
                    else:
                        stats["missing_attachments"] += 1
                        f.write(
                            '<div class="attachment-note">'
                            f'Adjunto referenciado pero no encontrado localmente: {html.escape(transfer)} · '
                            f'{html.escape(mime or "sin MIME")} · {html.escape(str(total_bytes))} bytes'
                            '</div>'
                        )

                f.write("</div>")

            f.write("</div>\n")

        f.write("</body>\n</html>\n")

    return out_html, img_dir, work_dir, stats


def main() -> None:
    print("Exportador interactivo de Mensajes/iMessage a HTML imprimible")
    print("No modifica chat.db. No borra nada. Crea archivos nuevos en ~/Downloads.")
    print("Versión v2: portable, HTML, message.text + attributedBody.\n")

    check_requirements()

    chats = list_chats(limit=80)
    chosen = choose_chat(chats)

    out_html, img_dir, work_dir, stats = export_chat(chosen)

    print("\nExportación terminada.")
    print(f"HTML: {out_html}")
    print(f"Imágenes/adjuntos copiados en: {img_dir}")
    print(f"Temporales conservados en: {work_dir}")
    print()
    print("Resumen:")
    print(f"  Mensajes exportados: {stats['messages']}")
    print(f"  Mensajes con message.text directo: {stats['message_text_used']}")
    print(f"  Mensajes tratados vía attributedBody/Swift: {stats['attributed_body_used']}")
    print(f"  Adjuntos referenciados: {stats['attachments']}")
    print(f"  Imágenes copiadas: {stats['images']}")
    print(f"  Adjuntos no encontrados localmente: {stats['missing_attachments']}")
    print("\nPara generar PDF: abre el HTML y usa Archivo > Imprimir > PDF > Guardar como PDF.")

    if ask_yes_no("¿Abrir el HTML ahora?", default=True):
        subprocess.run(["open", str(out_html)], check=False)


if __name__ == "__main__":
    main()
