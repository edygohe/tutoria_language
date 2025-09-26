import uvicorn
import sys
import os

# Añadimos el directorio 'src' al path de Python para que encuentre el módulo 'language_tutor'

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    """
    Punto de entrada para lanzar el servidor de la API.
    
    Este script inicia un servidor Uvicorn que sirve la aplicación FastAPI
    definida en 'language_tutor.api:app'.
    
    - app: La ruta de importación al objeto de la aplicación FastAPI.
    - host: "0.0.0.0" para que sea accesible desde la red local.
    - port: El puerto en el que se ejecutará el servidor.
    - reload: True para que el servidor se reinicie automáticamente al detectar
      cambios en el código, ideal para desarrollo.
    """
    uvicorn.run("language_tutor.api:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["src"])