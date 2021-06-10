from bs4 import BeautifulSoup
from abc import ABC
from typing import Any, List, Dict

class BaseParser(ABC):

    def parse(self, text: str, rules: List[Dict[str, str]]) -> List[Dict[str, str]]:
        return NotImplemented


class HTMLContentParser(BaseParser):
    pass
