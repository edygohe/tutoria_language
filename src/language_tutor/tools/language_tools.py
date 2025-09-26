import os
import logging
import re
from openai import OpenAI
from num2words import num2words
from ..config import settings

# Configura un logger básico
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def transcribe_audio(file_path: str) -> str:
    """
    Transcribe un archivo de audio a texto utilizando la API Whisper de OpenAI.

    :param file_path: La ruta al archivo de audio a transcribir.
    :return: El texto transcrito o un mensaje de error.
    """
    logging.info(f"Iniciando transcripción para el archivo: {file_path}...")

    if not settings.OPENAI_API_KEY:
        return "Error: La clave de API de OpenAI (OPENAI_API_KEY) no está configurada en el archivo .env."

    if not os.path.exists(file_path):
        return f"Error: El archivo de audio no se encontró en la ruta: {file_path}"

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        logging.info(f"Transcripción exitosa: '{transcription.text}'")
        return transcription.text
    except Exception as e:
        error_message = f"Error al transcribir el audio: {e}"
        logging.error(error_message, exc_info=True)
        return error_message

# Configura un logger básico
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def text_to_speech(text: str) -> str:
    """
    Convierte texto a voz usando la API de OpenAI y guarda el archivo.
    
    :param text: El texto a convertir en voz.
    :return: La ruta al archivo de audio generado o un mensaje de error.
    """
    logging.info(f"Iniciando síntesis de voz para el texto: '{text}'...")
    
    if not settings.OPENAI_API_KEY:
        error_message = "Error: La clave de API de OpenAI (OPENAI_API_KEY) no está configurada en el archivo .env."
        logging.error(error_message)
        return error_message
        
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Elige un modelo y una voz. 'tts-1' es el modelo estándar.
        # 'alloy' es una de las voces disponibles. Puedes probar otras como 'nova', 'echo', etc.
        
        # Pre-procesar el texto para mejorar las pausas
        processed_text = text.replace('\n\n', '... ').replace(': ', ': ... ')

        # Forzar la pronunciación de números en inglés usando num2words.
        # Esto evita que el motor de TTS se confunda con el texto bilingüe (ej. "twenty cinco").
        def replace_numbers_in_quotes(match):
            # match.group(1) es el contenido dentro de las comillas
            content = match.group(1)
            # Reemplazamos los números solo dentro de este contenido
            content_with_words = re.sub(r'\d+', lambda m: num2words(int(m.group(0)), lang='en'), content)
            return f'"{content_with_words}"'
        processed_text = re.sub(r'"(.*?)"', replace_numbers_in_quotes, processed_text, flags=re.DOTALL)

        response = client.audio.speech.create(
            model="tts-1-hd", # Usamos el modelo de alta definición para mayor calidad.
            voice="alloy", 
            input=processed_text,
            speed=0.80  # Reducimos la velocidad a 80% para una dicción muy clara y pausada.
        )
        
        # Guardar la respuesta de audio directamente en un archivo
        filename = os.path.join("data", ".uploads", f"response_{os.urandom(4).hex()}.mp3")
        response.stream_to_file(filename)
        
        logging.info(f"Archivo de audio guardado como '{filename}'.")
        return filename
    except Exception as e:
        error_message = f"Error durante la síntesis de voz con OpenAI: {e}"
        logging.error(error_message, exc_info=True)
        return error_message
