import httpx
import logging
import io
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import sys
import os

# Añadimos el directorio 'src' al path de Python para que encuentre el módulo 'language_tutor'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

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
IMAGE_API_URL = "http://127.0.0.1:8000/generate-image-from-text/"
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
        voice_bytearray = await voice_file.download_as_bytearray()

        # Prepara los datos para enviar a la API (multipart/form-data)
        files = {'file': ('voice_message.ogg', io.BytesIO(voice_bytearray), 'audio/ogg')}
        
        # Usamos un cliente asíncrono para no bloquear el bot
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Llama a la API de agentes
            logger.info(f"Enviando audio a la API en {AGENT_API_URL}...")
            response = await client.post(AGENT_API_URL, files=files)

            if response.status_code == 200:
                # 1. Obtener la respuesta de texto de los agentes
                text_response = response.json().get("response", "No se recibió una respuesta de texto válida.")
                logger.info(f"Respuesta de texto recibida de la API: '{text_response}'")

                # 2. Llamar al endpoint de imagen para generar la imagen de feedback
                logger.info(f"Solicitando generación de imagen a {IMAGE_API_URL}...")
                image_response = await client.post(IMAGE_API_URL, json={"text": text_response})
                if image_response.status_code == 200:
                    await update.message.reply_photo(photo=image_response.content)
                else:
                    logger.error(f"Error en la API de imagen: {image_response.status_code} - {image_response.text}")
                    await update.message.reply_text(text_response) # Si falla la imagen, enviamos el texto.

                # 3. Llamar al endpoint para generar el audio
                logger.info(f"Solicitando síntesis de voz a {TTS_API_URL}...")
                tts_response = await client.post(TTS_API_URL, json={"text": text_response})

                if tts_response.status_code == 200:
                    # 4. Enviar la respuesta de audio
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