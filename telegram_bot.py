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
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # --- PASO 1: Obtener el feedback ---
            logger.info(f"Solicitando feedback a la API...")
            feedback_response = await client.post(AGENT_API_URL, data={"team_name": "detailed_feedback_team"}, files=files)

            if feedback_response.status_code == 200:
                feedback_text = feedback_response.json().get("response")
                if not feedback_text:
                    await update.message.reply_text("No se pudo generar el feedback.")
                    return

                # Enviar la imagen de feedback
                image_response = await client.post(IMAGE_API_URL, json={"text": feedback_text})
                if image_response.status_code == 200:
                    await update.message.reply_photo(photo=image_response.content)
                else:
                    await update.message.reply_text(f"Error al generar imagen: {image_response.text}")

                # Enviar el audio del feedback
                tts_response = await client.post(TTS_API_URL, json={"text": feedback_text})
                if tts_response.status_code == 200:
                    await update.message.reply_voice(voice=tts_response.content)
                else:
                    await update.message.reply_text(f"Error al generar audio: {tts_response.text}")

            else:
                await update.message.reply_text(f"Error al obtener feedback: {feedback_response.text}")
                return

            # --- PASO 2: Obtener la respuesta conversacional ---
            # Reutilizamos el archivo de audio para una segunda llamada
            files_for_conversation = {'file': ('voice_message.ogg', io.BytesIO(voice_bytearray), 'audio/ogg')}
            logger.info(f"Solicitando continuación de la conversación a la API...")
            conversation_response = await client.post(AGENT_API_URL, data={"team_name": "direct_conversation_team"}, files=files_for_conversation)

            if conversation_response.status_code == 200:
                conversation_text = conversation_response.json().get("response")
                if not conversation_text:
                    logger.warning("No se generó respuesta conversacional.")
                    return

                # Generar y enviar el audio de la respuesta conversacional
                tts_response_conv = await client.post(TTS_API_URL, json={"text": conversation_text})
                if tts_response_conv.status_code == 200:
                    await update.message.reply_voice(voice=tts_response_conv.content)
                else:
                    await update.message.reply_text(f"Error al generar audio de respuesta: {tts_response_conv.text}")
            else:
                await update.message.reply_text(f"Error al continuar la conversación: {conversation_response.text}")

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