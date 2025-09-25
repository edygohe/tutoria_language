import requests
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from language_tutor.config import settings
# Configura el logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN ---
# Lee la configuración desde el objeto centralizado
TELEGRAM_TOKEN = settings.TELEGRAM_TOKEN
AGENT_API_URL = "http://127.0.0.1:8000/process-audio/"
TTS_API_URL = "http://127.0.0.1:8000/synthesize-speech/"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start."""
    await update.message.reply_text("¡Hola! Soy tu tutor de idiomas. Envíame un mensaje de voz en inglés y te responderé.")


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa los mensajes de voz."""
    voice = update.message.voice
    if not voice:
        return

    await update.message.reply_text("Recibido. Procesando tu audio...")

    try:
        # Descarga el archivo de voz de Telegram
        voice_file = await voice.get_file()
        voice_data = await voice_file.download_as_bytearray()

        # Prepara los datos para enviar a la API (multipart/form-data)
        files = {'file': ('voice_message.ogg', voice_data, 'audio/ogg')}
        
        # Llama a la API de agentes
        logger.info(f"Enviando audio a la API en {AGENT_API_URL}...")
        response = requests.post(AGENT_API_URL, files=files)

        if response.status_code == 200:
            # 1. Obtener y enviar la respuesta de texto
            text_response = response.json().get("response", "No se recibió una respuesta de texto válida.")
            logger.info(f"Respuesta de texto recibida de la API: '{text_response}'")
            await update.message.reply_text(text_response)

            # 2. Llamar al nuevo endpoint para generar el audio
            logger.info(f"Solicitando síntesis de voz a {TTS_API_URL}...")
            tts_response = requests.post(TTS_API_URL, json={"text": text_response})

            if tts_response.status_code == 200:
                # 3. Enviar la respuesta de audio
                logger.info("Respuesta de audio recibida. Enviando al usuario...")
                await update.message.reply_voice(voice=tts_response.content)
            else:
                logger.error(f"Error en la API de TTS: {tts_response.status_code} - {tts_response.text}")
                await update.message.reply_text("(No se pudo generar el audio de la respuesta).")
        else:
            logger.error(f"Error de la API: {response.status_code} - {response.text}")
            await update.message.reply_text(f"Lo siento, ocurrió un error al enviar tu audio. (Error: {response.status_code})")

    except Exception as e:
        logger.error(f"Error al procesar el mensaje de voz: {e}", exc_info=True)
        await update.message.reply_text("Lo siento, un error inesperado ocurrió.")


def main() -> None:
    """Inicia el bot de Telegram."""
    if not TELEGRAM_TOKEN:
        print("Error: La variable TELEGRAM_TOKEN no está configurada en tu archivo .env.")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))

    print("Iniciando bot de Telegram... Presiona Ctrl+C para detener.")
    application.run_polling()

if __name__ == "__main__":
    main()