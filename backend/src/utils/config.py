from utils.config_handler import load_config
from utils.path_tool import get_source_path

vector_config = load_config(config_path=get_source_path('config/vector_store.yaml'))
prompt_config = load_config(config_path=get_source_path('config/prompt.yaml'))
agent_config = load_config(config_path=get_source_path('config/agent.yaml'))

if __name__ == '__main__':
    print(vector_config)
    print(prompt_config)
    print(agent_config)
