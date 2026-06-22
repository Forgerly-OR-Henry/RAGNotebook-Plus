from utils.config_handler import load_config
from utils.path_tool import get_config_path

agent_config = load_config(config_path=get_config_path("agent.yaml"))

if __name__ == '__main__':
    print(agent_config)
