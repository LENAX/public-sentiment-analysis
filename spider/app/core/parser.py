from bs4 import BeautifulSoup
from lxml import etree
from abc import ABC
from typing import Any, List, Dict, Union, Set, Callable, Optional
from ..models.data_models import (
    ParseRule, ParseResult, URL, HTMLData
)
from ..enums import ParseRuleType
from .parse_driver import ParseDriver
import re

class BaseParsingStrategy(ABC):
    """ Base strategy for parsing text
    """

    def parse(self, text: str, rules: List[ParseRule]) -> List[ParseResult]:
        return NotImplemented


class HTMLContentParser(BaseParsingStrategy):
    
    def parse(self, text: str, rules: List[ParseRule]) -> List[ParseResult]:
        return NotImplemented


class LinkParser(BaseParsingStrategy):
    """ Parses a html text and finds all links

    Attributes:
        parse_driver_class: Parser Class for low level html string parsing
    """
    
    def __init__(self, parse_driver_class: ParseDriver):
        self._parser = parse_driver_class

    def _valid_link(self, link):
        return link and len(link) and (link.startswith('http') or link.startswith('/'))


    def parse(self, text: str, rules: List[ParseRule]) -> List[URL]:
        parsed_html = self._parser(text)
        parsed_links = set()

        for rule in rules:
            # match all links using provided rules
            links = parsed_html.select_elements_by(
                        selector_type=rule.rule_type,selector_expression=rule.rule)
            for link_url in parsed_html.get_element_attributes(links, 'href'):
                if self._valid_link(link_url):
                    parsed_links.add(URL(url=link_url))

        return list(parsed_links)
        

class PageParser(BaseParsingStrategy):

    def parse(self, text: str, rules: List[ParseRule]) -> List[ParseResult]:
        return NotImplemented



if __name__ == "__main__":
    import requests

    # link parsing
    page_text = requests.get(
        "http://www.baidu.com/s?wd=beautifulsoup&rsv_spt=1&rsv_iqid=0xea44a89400010d1e&issp=1&f=8&rsv_bp=1&rsv_idx=2&ie=utf-8&tn=baiduhome_pg&rsv_enter=1&rsv_dl=tb&rsv_sug3=8&rsv_sug1=6&rsv_sug7=100&sug=beautiful&rsv_n=1&rsv_t=56c5exdpUaui0yU6%2BIcYEwvmv%2BQBZAcdY4sqaeNWH6dmK6AyZ4T%2B5zaatRDVRbJ%2BAMeu&rsv_sug2=0&rsv_btype=i&inputT=4656&rsv_sug4=4656").text
    link_parser = LinkParser(parse_driver_class=ParseDriver)
    parsed_links = link_parser.parse(page_text,
                                     rules=[
                                        ParseRule(
                                            rule_type='xpath', 
                                            rule='//h3/a')
                                    ])
    print(parsed_links)
    print(len(parsed_links))
