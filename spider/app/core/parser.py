import re
from abc import ABC
from typing import List, Callable
from ..models.data_models import (
    ParseRule, ParseResult, URL, HTMLData
)
from .parse_driver import ParseDriver
from .exceptions import InvalidBaseURLException


class BaseParsingStrategy(ABC):
    """ Base strategy for parsing text
    """

    def parse(self, text: str, rules: List[ParseRule]):
        return NotImplemented


class HTMLContentParser(BaseParsingStrategy):

    def __init__(self, parse_driver_class: ParseDriver):
        self._parser = parse_driver_class

    def _valid(self, content):
        return content and len(content)
    
    def parse(self, text: str, rules: List[ParseRule]) -> List[ParseResult]:
        """ Parse html and return a list of ParseResult given a list of ParseRule.
        Suppose you want to get title, date, author and content from this blog post [https://cuiqingcai.com/1319.html].
        You provide a list of ParseRule, which specifies the fields and rules to extract these fields.
        In this case, you provide a list of rules like

        [ParseRule(
            field_name='title',
            rule_type='xpath',
            rule='//article/header/h1'),
         ParseRule(
            field_name='date',
            rule_type='xpath',
            rule='//article/header/div/span[1]/span[3]/a'),
         ParseRule(
            field_name='author',
            rule_type='xpath',
            rule='//article/header/div/span[2]/time'),
         ParseRule(
            field_name='content',
            rule_type='xpath',
            rule="//article/div")]

        Hints:
            text content can usually be found in p, div, span and a tags

        Args:
            text: HTML string to parse
            rules: a list of (field_name, rule, rule_type) objects

        Returns:
            List[ParseResult]: a list of (field_name, field_value) objects.
        """

        parsed_html = self._parser(text)
        parsed_content = []

        for rule in rules:
            # match all links using provided rules
            contents = parsed_html.select_elements_by(
                selector_type=rule.rule_type, selector_expression=rule.rule)
            if len(contents) > 0:
                for content_attributes in parsed_html.get_element_attributes(contents, ['text']):
                    if self._valid(content_attributes['text']):
                        parsed_content.append(
                            ParseResult(name=rule.field_name, value=content_attributes['text'].strip()))
            else:
                parsed_content.append(
                    ParseResult(name=rule.field_name, value=''))

        return parsed_content


class LinkParser(BaseParsingStrategy):
    """ Parses a html text and finds all links

    Attributes:
        parse_driver_class: Parser Class for low level html string parsing
    """
    
    def __init__(self, parse_driver_class: ParseDriver,
                 link_pattern: re.Pattern=re.compile(
                 "(\b(https?|ftp|file)://)?[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]"),
                 base_url: str = None
    ):
        self._parser = parse_driver_class
        self._link_pattern = link_pattern
        self._base_url = base_url

    def _valid_link(self, link):
        return self._link_pattern.match(link)

    @property
    def link_pattern(self):
        return self._link_pattern

    @link_pattern.setter
    def link_pattern(self, link_pattern: re.Pattern):
        self._link_pattern = link_pattern

    @property
    def base_url(self):
        return self._base_url

    @base_url.setter
    def base_url(self, base_url: re.Pattern):
        if self._link_pattern.match(base_url):
            self._base_url = base_url
        else:
            raise InvalidBaseURLException("Please provide a valid base url starting with (http|https|ftp)")
    

    def parse(self, text: str, rules: List[ParseRule]) -> List[ParseResult]:
        parsed_html = self._parser(text)
        parsed_links = set()

        for rule in rules:
            # match all links using provided rules
            links = parsed_html.select_elements_by(
                        selector_type=rule.rule_type,selector_expression=rule.rule)
                        
            for link_url in parsed_html.get_element_attributes(links, ['text', 'href']):
                if self._valid_link(link_url['href']):
                    url = link_url['href']
                    if not url.startswith("http") and self._base_url is not None:
                        # try to convert relative url to absolute url
                        url = f"{self._base_url}/{url}"

                    parsed_links.add(ParseResult(
                        name=link_url['text'], value=url))

        return list(parsed_links)


class DatetimeParser(BaseParsingStrategy):
    
    def __init__(self, parse_driver_class: ParseDriver):
        self._parser = parse_driver_class

    def parse(self, text: str, rules: List[ParseRule],
              datetime_formatter: Callable = None) -> List[ParseResult]:
        """ Parses datetime from webpages 

        Allow processing datetime text using a datetime formatter.
        If the datetime text is not in a standard format, like "3 days ago",
        you can write custom logic to convert it to standard format.

        Args:
            text
            rules
            datetime_formatter

        Returns:
            List[ParseResult]
        """
        
        parsed_html = self._parser(text)
        parsed_dt = []

        for rule in rules:
            # match all datetime using provided rules
            datetimes = parsed_html.select_elements_by(
                selector_type=rule.rule_type, selector_expression=rule.rule)

            for datetime_element in parsed_html.get_element_attributes(datetimes, ['text']):
                if datetime_element and len(datetime_element):
                    datetime_text = datetime_element['text']
                    if datetime_formatter:
                        datetime_text = datetime_formatter(datetime_text)
                    parsed_dt.add(ParseResult(name=rule.field_name, value=datetime_text))

        return parsed_dt


class ParserContext(object):

    def __init__(self, parsing_strategy: BaseParsingStrategy):
        self._parsing_strategy = parsing_strategy

    @property
    def parsing_strategy(self) -> BaseParsingStrategy:
        return self._parsing_strategy

    @parsing_strategy.setter
    def parsing_strategy(self, parsing_strategy: BaseParsingStrategy) -> None:
        self._parsing_strategy = parsing_strategy

    def parse(self, text: str, rules: List[ParseRule]) -> List[ParseResult]:
        return self._parsing_strategy.parse(text, rules)


class ParserContextFactory(object):
    __parser_classes__ = {
        'general_parser': HTMLContentParser,
        'link_parser': LinkParser,
        'datetime_parser': DatetimeParser
    }
    __default_parser_cls__ = HTMLContentParser
    __parser_driver__ = ParseDriver
    __parser_context__ = ParserContext
    

    @property
    def parser_classes(cls):
        return list(cls.__parser_classes__.keys())

    @property
    def parser_driver(cls):
        return cls.__parser_driver__

    @classmethod
    def create(cls, parser_name: str) -> ParserContext:
        parser_cls = cls.__parser_classes__.get(parser_name, cls.__default_parser__)(cls.__default_parser__)
        return cls.__parser_context__(parser_cls(cls.__parser_driver__))




if __name__ == "__main__":
    import requests
    import re

    # link parsing
    def test_link_parsing():
        page_text = requests.get(
            "http://www.tianqihoubao.com/").text
        # print(page_text)
        link_parser = LinkParser(
            parse_driver_class=ParseDriver, base_url='http://www.tianqihoubao.com')
        parsed_links = link_parser.parse(page_text,
                                        rules=[
                                            ParseRule(
                                                field_name='province',
                                                rule_type='xpath', 
                                                rule='//tr[3]/td[3]/a')
                                        ])
        print(parsed_links)
        print(len(parsed_links))

    def test_content_parsing():
        page_text = requests.get(
            "https://cuiqingcai.com/1319.html").text
        parser = HTMLContentParser(parse_driver_class=ParseDriver)
        contents = parser.parse(page_text,
                                rules=[
                                    ParseRule(
                                        field_name='title',
                                        rule_type='xpath',
                                        rule='//article/header/h1'),
                                    ParseRule(
                                        field_name='date',
                                        rule_type='xpath',
                                        rule='//article/header/div/span[1]/span[3]/a'),
                                    ParseRule(
                                        field_name='author',
                                        rule_type='xpath',
                                        rule='//article/header/div/span[2]/time'),
                                    ParseRule(
                                        field_name='content',
                                        rule_type='xpath',
                                        rule="//article/div"),
                                ])
        print(contents)
        print(len(contents))

    def test_page_finding():
        page_text = requests.get(
            "https://search.douban.com/book/subject_search?search_text=java&cat=1001").text
        print(page_text)
        link_parser = LinkParser(parse_driver_class=ParseDriver)
        parsed_links = link_parser.parse(page_text,
                                         rules=[
                                             ParseRule(
                                                 rule_type='xpath',
                                                 rule="//a[contains(@href,'start=')]")
                                         ])
        print(parsed_links)
        print(len(parsed_links))

    
    def test_flexible_parse():
        page_text = requests.get(
            "https://cuiqingcai.com/1319.html").text
        parser_context = ParserContext(
            LinkParser(parse_driver_class=ParseDriver))
        parse_result = parser_context.parse(page_text,
                                            rules=[ParseRule(
                                                field_name='date',
                                                rule_type='xpath',
                                                rule='//article/header/div/span[1]/span[3]/a')])
        print(parse_result)

        # switch strategy
        parser_context.parsing_strategy = HTMLContentParser(parse_driver_class=ParseDriver)
        parse_result = parser_context.parse(page_text,
                                            rules=[
                                                ParseRule(
                                                    field_name='title',
                                                    rule_type='xpath',
                                                    rule='//article/header/h1'),
                                                ParseRule(
                                                    field_name='date',
                                                    rule_type='xpath',
                                                    rule='//article/header/div/span[1]/span[3]/a'),
                                                ParseRule(
                                                    field_name='author',
                                                    rule_type='xpath',
                                                    rule='//article/header/div/span[2]/time'),
                                                ParseRule(
                                                    field_name='content',
                                                    rule_type='xpath',
                                                    rule="//article/div"),
                                            ])
        print(parse_result)

    test_to_run = test_content_parsing
    test_to_run()
