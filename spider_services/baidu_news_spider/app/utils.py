import ujson
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


def get_area_codes(data_path):

    with open(data_path, 'r') as f:
        area_code_data = ujson.loads(f.read())

    city_area_codes = [f"{area['code']}0000" for area in area_code_data]
    return city_area_codes


def get_area_code_dict(data_path):
    area_code_dict = {}

    with open(data_path, 'r') as f:
        area_code_data = ujson.loads(f.read())

    for area in area_code_data:
        cities = area['children']
        province_name = area['name']
        area_code_dict[province_name] = f"{area['code']}0000"
        area_code_dict[f"{area['code']}0000"] = province_name

        for city in cities:
            city_name = f"{province_name}{city['name']}"
            code = city['code'] if len(
                city['code']) == 6 else f"{city['code']}00"
            area_code_dict[city_name] = code
            area_code_dict[code] = city_name

    return area_code_dict
