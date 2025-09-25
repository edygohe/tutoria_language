import autogen
import json
import os
from language_tutor.config import get_llm_config, settings
from language_tutor.tools.language_tools import transcribe_audio, text_to_speech
from language_tutor.agents.base_agents import create_assistant_agent

def run_team_conversation_and_get_text_response(team_name: str, user_request: str) -> str | None:
    llm_config = get_llm_config()
    if not llm_config:
        print("Error: Could not load LLM configuration. Make sure your .env file is configured.")
        return None

    # Ensure the provider is OpenAI for Whisper
    if settings.LLM_PROVIDER != "openai":
        print("Warning: Audio transcription requires LLM_PROVIDER='openai' in your .env to use Whisper.")

    # 3. Cargar la configuración del equipo y crear los agentes dinámicamente
    config_path = os.path.join(os.path.dirname(__file__), 'configs', 'team_configs.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        teams = json.load(f)
    
    team_config = teams.get(team_name)
    if not team_config:
        print(f"Error: Team '{team_name}' not found in configuration.")
        return None

    # Creamos una configuración de LLM específica que INCLUYE las herramientas.
    # Solo se la daremos a los agentes que la necesiten para que sepan cómo proponer su uso.
    llm_config_with_tools = llm_config.copy()
    llm_config_with_tools["tools"] = [
        {
            "type": "function",
            "function": {
                "name": "transcribe_audio",
                "description": "Transcribes an audio file to text.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "The full path to the audio file."},
                    },
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "text_to_speech",
                "description": "Converts text to an audio file.",
                "parameters": {
                    "type": "object",
                    "properties": {"text": {"type": "string", "description": "The text to convert."}},
                    "required": ["text"],
                },
            },
        },
    ]

    user_proxy = autogen.UserProxyAgent(
       name="User_Proxy",
       human_input_mode="NEVER",
       max_consecutive_auto_reply=10,
       code_execution_config={"use_docker": False},  # Indica a autogen que no use Docker.
    )
    user_proxy.register_function(
        function_map={
            "transcribe_audio": transcribe_audio,
            "text_to_speech": text_to_speech,
        }
    )

    team_agents = [user_proxy]
    # Damos la config con herramientas solo a los agentes que las necesitan.
    for role_name in team_config["agent_roles"]:
        if role_name in ["Audio_Transcriber", "Speech_Synthesizer"]:
            agent = create_assistant_agent(llm_config_with_tools, role_name)
        else:
            agent = create_assistant_agent(llm_config, role_name)
        team_agents.append(agent)

    # 4. Configurar el GroupChat para la colaboración
    groupchat = autogen.GroupChat(agents=team_agents, messages=[], max_round=12)
    manager = autogen.GroupChatManager(
        groupchat=groupchat,
        llm_config=llm_config, # El manager necesita el LLM para interpretar las propuestas de herramientas.
        # Terminamos cuando el último agente del equipo haya hablado.
        is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    )
    groupchat.speaker_selection_method = "round_robin" # Forzar el orden de los turnos

    # 5. Start the conversation
    print(f"--- Starting conversation with team: {team_name} ---")
    user_proxy.initiate_chat(manager, message=user_request)

    # 6. Extraer la respuesta final de texto del Conversation_Partner
    for msg in reversed(groupchat.messages):
        if msg.get("name") == "Conversation_Partner":
            # Limpiamos la palabra TERMINATE si existe
            return msg.get("content", "").replace("TERMINATE", "").strip()
    
    return None