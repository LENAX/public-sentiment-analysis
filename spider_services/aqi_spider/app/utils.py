from yaml import load, dump
from yaml import CLoader as Loader, CDumper as Dumper
from ...common.models.request_models import (
    ScrapeRules, ParsingPipeline, ParseRule, KeywordRules, TimeRange
)
from typing import Any, Callable
from os import getcwd

def load_service_config(
    config_name: str,
    loader_func: Callable = load,
    loader_class: Any = Loader,
    config_class: Any = ScrapeRules,
    config_path: str = f"{getcwd()}/spider_services/service_configs"
) -> object:
    with open(f"{config_path}/{config_name}.yml", "r") as f:
        config_text = f.read()
        parsed_obj = loader_func(config_text, Loader=loader_class)
        config_obj = config_class.parse_obj(parsed_obj)
        return config_obj
