import os
import shutil
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from .main import run_team_conversation_and_get_text_response
from .tools.language_tools import text_to_speech
from .tools.image_tools import text_to_image

app = FastAPI(
    title="Language Tutor Agent Service",
    description="An API to interact with a team of language learning agents.",
    version="0.1.0",
)

UPLOADS_DIR = "data/.uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

@app.post("/process-audio/")
async def process_audio_to_text(
    team_name: str = Form("detailed_feedback_team"), # Usamos el nuevo equipo con lógica separada
    file: UploadFile = File(...)
):
    """
    Endpoint para subir un archivo de audio, procesarlo con agentes y devolver una respuesta de texto.
    """
    # Genera un nombre de archivo único para el audio de entrada
    file_extension = os.path.splitext(file.filename)[1] or ".ogg"
    temp_filename = f"{uuid.uuid4()}{file_extension}"
    input_path = os.path.join(UPLOADS_DIR, temp_filename)

    # Guarda el archivo subido en el servidor
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    user_request = f"""Start a conversation based on the following audio file: '{input_path}'.
Listen to what I say and respond naturally in the same language.
    """
    
    try:
        # Usamos run_in_threadpool para ejecutar el código síncrono de los agentes
        # sin bloquear el bucle de eventos de FastAPI.
        text_response = await run_in_threadpool(run_team_conversation_and_get_text_response, team_name=team_name, user_request=user_request)
        
        if text_response:
            return {"response": text_response}
        else:
            raise HTTPException(status_code=500, detail="Agent process finished but no text response was generated.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during agent processing: {e}")
    finally:
        # Limpieza del archivo de entrada
        if os.path.exists(input_path):
            os.remove(input_path)
            print(f"Cleaned up temporary input file: {input_path}")

@app.post("/synthesize-speech/")
async def synthesize_speech(
    text_input: dict,
    background_tasks: BackgroundTasks
):
    """
    Endpoint para convertir texto a voz.
    Recibe un JSON con texto y devuelve un archivo de audio.
    """
    text = text_input.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="No text provided for synthesis.")

    output_path = text_to_speech(text)

    if output_path and os.path.exists(output_path):
        background_tasks.add_task(os.remove, output_path)
        return FileResponse(path=output_path, media_type="audio/mpeg", filename=os.path.basename(output_path), background=background_tasks)
    else:
        raise HTTPException(status_code=500, detail="Failed to generate speech file.")

@app.post("/generate-image-from-text/")
async def generate_image(
    text_input: dict,
    background_tasks: BackgroundTasks
):
    """
    Endpoint para convertir texto a una imagen estilizada.
    """
    text = text_input.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="No text provided for image generation.")

    # Definir una ruta de salida temporal para la imagen
    output_filename = f"feedback_{uuid.uuid4()}.png"
    output_path = os.path.join(UPLOADS_DIR, output_filename)

    # Generar la imagen
    generated_path = text_to_image(text, output_path)
    if generated_path and os.path.exists(generated_path):
        background_tasks.add_task(os.remove, generated_path)
        return FileResponse(path=generated_path, media_type="image/png", filename=os.path.basename(generated_path), background=background_tasks)
    else:
        raise HTTPException(status_code=500, detail="Failed to generate image from text.")