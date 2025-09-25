import autogen
import json
import os

def create_assistant_agent(llm_config: dict, role_name: str) -> autogen.AssistantAgent:
    """
    Crea un agente Asistente cargando su rol y nombre desde un archivo de configuración.

    Args:
        llm_config: La configuración del LLM para el agente.
        role_name: El nombre del rol a cargar desde el archivo de configuración.

    Returns:
        Una instancia de autogen.AssistantAgent.
    """
    # Construir la ruta al archivo de configuración de roles
    config_path = os.path.join(os.path.dirname(__file__), '..', 'configs', 'agent_roles.json')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        roles = json.load(f)
    
    agent_config = roles.get(role_name, roles["Default"])

    assistant = autogen.AssistantAgent(
        name=agent_config["name"],
        llm_config=llm_config,
        system_message=agent_config["system_message"],
    )
    return assistant

