""" A facade for BeautifulSoup4 and lxml

ParseDriver class patches the lack of xpath support in BeautifulSoup by adding xpath support from lxml.
Then it provides a unified interface for its users.
"""

from bs4 import BeautifulSoup
from bs4.element import Tag
from lxml import etree
from lxml.html import fromstring
from lxml.etree import Element
from functools import partial
from typing import Callable, List, Any, Union, Dict, Generator
from gne import GeneralNewsExtractor

class ParseDriver(GeneralNewsExtractor):
    """ Creates a Facade for BeautifulSoup, lxml and GeneralNewsExtractor.
    
    This class will primarily use BeautifulSoup since it is more user-friendly.
    To patch xpath selection functionality, we use lxml under the hood.
    """

    def __init__(self, text: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parsed_text = BeautifulSoup(text, 'lxml')
        self.text = text
        self._initialize_selectors()

    def _initialize_selectors(self):
        self._link_selector_mappings = {
            # lxml's xpath select has to bind with an etree object during runtime
            'xpath': None, 
            'css_selector': BeautifulSoup.select,
            'regex': BeautifulSoup.find_all,
            'class_name': BeautifulSoup.find_all,
            'element_id': BeautifulSoup.find,
            'text_content': BeautifulSoup.find_all
        }

    def _get_selector(self, selector: str, parsed_text: BeautifulSoup) -> Callable:
        if selector == 'xpath':
            self._link_selector_mappings['xpath'] = fromstring(self.text).xpath
            return self._link_selector_mappings['xpath']
        else:
            return partial(
                self._link_selector_mappings[selector],
                parsed_text
            )

    def _get_attribute_failed(self, attribute_value) -> bool:
        return attribute_value is None or len(attribute_value) == 0

    def _get_element_attribute(self, element: Union[Tag, Element], attribute_name: str) -> str:
        """ Due to the poor api design and chaotic nature of html elements, we need to try many ways
            to get attributes from an element.
        """
        
        attribute_value = ""
        # either the attribute is in element's attribute dict, or
        # it is one of the element object's field
        try:
            # TODO: refactor this using an {attribute: getter} mapping.
            if (self._get_attribute_failed(attribute_value) and
                attribute_name == 'text' and hasattr(element, 'text_content')):
                # special case where we need to get text content from element's children
                attribute_value = element.text_content()
            if self._get_attribute_failed(attribute_value) and hasattr(element, attribute_name):
                attribute_value = getattr(element, attribute_name)
            if self._get_attribute_failed(attribute_value) and hasattr(element, 'get'):
                attribute_value = element.get(attribute_name)
            if self._get_attribute_failed(attribute_value) and hasattr(element, 'attrib'):
                attribute_value = element.attrib[attribute_name]
            if (self._get_attribute_failed(attribute_value) and
                hasattr(element, 'attrs') and
                element.attrs and attribute_name in element.attrs):
                attribute_value = element.attrs[attribute_name]
        except KeyError as e:
            print(KeyError(f"{e} does not exist in element.attrib"))
        except AttributeError as e:
            print(e)

        return attribute_value

    def select_elements_by(self, selector_type:str, selector_expression: str) -> List[Any]:
        """ Select element given html/xml text, rule and attribute

        Args:
            text: html/xml text
            selector_type: one of (xpath, css_selector, regex, class_name, element_id, text_content)
            selector_expression: an expression of (xpath, css_selector, regex, class_name, element_id, text_content)
        """
        # get an element selector
        selector = self._get_selector(selector_type, self.parsed_text)
        # select elements from the element tree
        selected_elements = selector(selector_expression)
        
        return selected_elements

    def select_element(self,
                       selector_type: str,
                       selector_expression: str) -> Generator[str, str, Union[Tag, Element]]:
        """ Select element given html/xml text, rule and attribute

        Args:
            text: html/xml text
            selector_type: one of (xpath, css_selector, regex, class_name, element_id, text_content)
            selector_expression: an expression of (xpath, css_selector, regex, class_name, element_id, text_content)
        
        Returns:
            Generator[Union[Tag, Element]]
        """
        # get an element selector
        selector = self._get_selector(selector_type, self.parsed_text)
        # select elements from the element tree
        for selected_elements in selector(selector_expression):
            yield selected_elements

    def get_element_attributes(self, 
                               elements: List[Union[Tag, Element]],
                               attribute_names: List[str]) -> List[Dict[str, str]]:
        return [{attribute_name: self._get_element_attribute(element, attribute_name) for attribute_name in attribute_names}
                for element in elements]


class GeneralNewsParserDriver(ParseDriver, GeneralNewsExtractor):

     def __init__(self, text: str, *args, **kwargs):
        ParseDriver.__init__(self, text, *args, **kwargs)
        GeneralNewsExtractor.__init__(self)


if __name__ == "__main__":
    import requests
    from gne import GeneralNewsExtractor

    page_text = requests.get(
        "https://new.qq.com/omn/20210618/20210618A02OG800.html").text
    # parse_driver = ParseDriver(page_text)
    # links = parse_driver.select_elements_by('xpath', "//h3/a")
    # attributes = parse_driver.get_element_attributes(links, ['text', 'href'])
    # print(attributes)

    parse_driver = ParseDriver(page_text)
    result = parse_driver.extract(page_text)
    print(result)


