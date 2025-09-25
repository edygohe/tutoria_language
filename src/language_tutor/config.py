import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# 1. Define la clase de configuración usando Pydantic para leer desde .env
class Settings(BaseSettings):
    """
    Centraliza la configuración de la aplicación, cargando valores desde
    un archivo .env para mantener las claves seguras y fuera del código.
    """
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # Proveedor de LLM a utilizar: "gemini" o "openai"
    LLM_PROVIDER: str = "gemini"
    
    # --- Configuración de Google Gemini ---
    GOOGLE_API_KEY: str | None = None
    GEMINI_MODEL_NAME: str = "gemini-pro"

    # --- Configuración de OpenAI ---
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL_NAME: str = "gpt-4o-mini"

    # --- Configuración del Bot de Telegram ---
    TELEGRAM_TOKEN: str | None = None

# 2. Crea una instancia única para ser usada en toda la aplicación
settings = Settings()

def get_llm_config():
    """
    Carga la configuración del LLM para AutoGen basándose en el proveedor
    especificado en las variables de entorno.
    """
    if settings.LLM_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            print("Error: LLM_PROVIDER es 'openai' pero OPENAI_API_KEY no está configurada en tu .env")
            return None
        config_list = [{"model": settings.OPENAI_MODEL_NAME, "api_key": settings.OPENAI_API_KEY}]
    elif settings.LLM_PROVIDER == "gemini":
        if not settings.GOOGLE_API_KEY:
            print("Error: LLM_PROVIDER es 'gemini' pero GOOGLE_API_KEY no está configurada en tu .env")
            return None
        config_list = [{"model": settings.GEMINI_MODEL_NAME, "api_key": settings.GOOGLE_API_KEY}]
    else:
        print(f"Error: Proveedor de LLM no soportado: '{settings.LLM_PROVIDER}'. Opciones válidas: 'openai', 'gemini'.")
        return None
        
    return {"config_list": config_list}
