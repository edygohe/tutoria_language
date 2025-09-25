import os
import shutil
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.concurrency import run_in_threadpool
from .main import run_team_conversation_and_get_text_response

app = FastAPI(
    title="Language Tutor Agent Service",
    description="An API to interact with a team of language learning agents.",
    version="0.1.0",
)

UPLOADS_DIR = "data/.uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

@app.post("/process-audio/")
async def process_audio_to_text(
    team_name: str = Form("grammar_check_conversation_team"), # Usamos el equipo que termina en texto
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