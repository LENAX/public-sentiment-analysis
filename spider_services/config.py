from pyaml_env import parse_config
import os
import logging

dir_path = os.path.dirname(os.path.realpath(__file__))
app_config = parse_config(f"{dir_path}/config.yml")
env = os.getenv("APP_ENV", "local_development")
config = app_config[env]

logging.info(f"Environent: {env}")
logging.info(f"config: {config}")
