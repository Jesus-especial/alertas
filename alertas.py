import html
import logging
import os
from typing import Optional

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Carga .env si existe (uso local). En Railway las variables vienen del panel.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("alertas")

# ─────────────── IDs FIJOS ───────────────
ID_JEFE = 8349343339

CANAL_ALERTA_MANDAR = -1003912870630
CANAL_ALERTA_BAN = -1004308078934
CANAL_ALERTA_SAPO = -1004308078934
CANAL_ALERTA_PAGADO = -1003904688094
CANAL_PUBLICO = -1003399670981

# Token: variable de entorno primero, valor actual como respaldo.
TELEGRAM_TOKEN = os.environ.get(
    "TELEGRAM_ALERTAS_TOKEN",
    "9179671917:AAH-70-8yrHGi23NysgJakBzp914WF-XuBY",
).strip()


def formato_alerta_cliente(titulo: str, message, estado: str = "") -> str:
    chat = message.chat
    nombre = html.escape(chat.first_name or "No disponible")
    apellido = html.escape(chat.last_name or "No disponible")
    usuario = f"@{html.escape(chat.username)}" if chat.username else "No disponible"
    identificador = chat.id
    alerta = (
        f"<b>{html.escape(titulo)}</b>\n\n"
        f'<a href="tg://user?id={identificador}">Abrir perfil</a>\n'
        f"<b>ID:</b> <code>{identificador}</code>\n"
        f"<b>Usuario:</b> {usuario}\n"
        f"<b>Nombre:</b> {nombre}\n"
        f"<b>Apellido:</b> {apellido}"
    )
    if estado:
        alerta += f"\n\n<b>Bloqueo:</b> {html.escape(estado)}"
    return alerta


async def procesar_comando_business(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    titulo: str,
    canal_alerta: Optional[int],
    bloquear: bool = False,
) -> None:
    message = update.business_message or update.effective_message
    if not message:
        return

    # Verificar que el mensaje sea en un chat privado
    if message.chat.type != "private":
        return

    # Solo dentro de un chat business, o del jefe en el DM del bot
    if not message.business_connection_id and message.chat.id != ID_JEFE:
        log.info("Ignorado: chat %s no es business ni es el jefe.", message.chat.id)
        return

    # 1. Borrar el comando del chat del cliente
    if message.business_connection_id:
        try:
            await context.bot.delete_business_messages(
                business_connection_id=message.business_connection_id,
                message_ids=[message.message_id],
            )
            log.info("Comando borrado del chat %s.", message.chat.id)
        except TelegramError as e:
            log.warning("Error al borrar comando en chat %s: %s", message.chat.id, e)

    # 2. Banear al cliente del canal público si aplica
    estado_bloqueo = ""
    if bloquear:
        try:
            await context.bot.ban_chat_member(
                chat_id=CANAL_PUBLICO,
                user_id=message.chat.id,
            )
            estado_bloqueo = "Realizado"
            log.info("Usuario %s baneado del canal público.", message.chat.id)
        except TelegramError as e:
            estado_bloqueo = f"FALLÓ: {e}"
            log.error("Error al banear usuario %s del canal: %s", message.chat.id, e)

    # 3. Enviar la ficha al canal de alertas correspondiente
    if canal_alerta:
        texto = formato_alerta_cliente(titulo, message, estado_bloqueo)
        try:
            await context.bot.send_message(
                chat_id=canal_alerta,
                text=texto,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            log.info("Alerta '%s' enviada al canal %s.", titulo, canal_alerta)
        except TelegramError as e:
            log.error("Error al enviar alerta al canal %s: %s", canal_alerta, e)


async def router_business_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.business_message or update.effective_message
    if not message or not message.text:
        return

    texto = message.text.strip().lower()
    comando = texto.split()[0].split("@")[0]

    log.info("Comando detectado: '%s' en chat %s", comando, message.chat.id)

    if comando == "/ban":
        await procesar_comando_business(update, context, "HOSTIL DETECTADO", CANAL_ALERTA_BAN, bloquear=True)
    elif comando == "/mandar":
        await procesar_comando_business(update, context, "MANDAR VIDEO", CANAL_ALERTA_MANDAR)
    elif comando == "/sapo":
        await procesar_comando_business(update, context, "SAPO DETECTADO", CANAL_ALERTA_SAPO)
    elif comando == "/pagado":
        await procesar_comando_business(update, context, "PAGADO", CANAL_ALERTA_PAGADO)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Error en handler: %s", context.error, exc_info=context.error)


if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        raise SystemExit("Falta TELEGRAM_ALERTAS_TOKEN")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Captura mensajes regulares y de Telegram Business que contengan comandos
    app.add_handler(
        MessageHandler(
            (filters.UpdateType.BUSINESS_MESSAGE | filters.UpdateType.MESSAGE)
            & filters.Regex(r"^\s*/(ban|mandar|sapo|pagado)\b"),
            router_business_commands,
        )
    )

    app.add_error_handler(on_error)

    log.info("=== BOT INICIADO Y ESCUCHANDO ===")
    app.run_polling(
        allowed_updates=[
            "business_message",
            "business_connection",
            "message",
            "edited_business_message",
        ]
    )