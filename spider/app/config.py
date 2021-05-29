from pyaml_env import parse_config
import os 

dir_path = os.path.dirname(os.path.realpath(__file__))
app_config = parse_config(f"{dir_path}/config.yml")
config = app_config[os.getenv("APP_ENV", "local_development")]