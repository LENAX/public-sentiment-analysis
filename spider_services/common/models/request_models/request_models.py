from typing import Optional, List, Union
from pydantic import BaseModel, validator
from datetime import date, datetime
from ...enums import ContentType, JobType, Parser, ParseRuleType
from devtools import debug

class KeywordRules(BaseModel):
    """ Keywords to include or exclude """
    include: List[str] = []
    exclude: List[str] = []


class SizeLimit(BaseModel):
    max_pages: Optional[int]
    max_size: Optional[int]


class TimeRange(BaseModel):
    past_days: Optional[int]
    start_date: Optional[datetime]
    end_date: Optional[datetime]


class RegexPattern(BaseModel):
    patterns: Optional[List[str]] = []


class ParseRule(BaseModel):
    """ Defines the parse rule for a parser

    Fields:
        field_name: str,
        rule: str,
        rule_type: ParseRuleType   
        slice_str: Optional[Tuple[int, int]]
    """
    field_name: Optional[str]
    rule: str
    rule_type: ParseRuleType
    is_link: bool = False
    slice_str: Optional[List[int]]
    
    class Config:
        use_enum_values = True
        
    @validator("rule_type", pre=True)
    def parse_rule_type(cls, value):
        if not hasattr(ParseRuleType, value):
            rule_type = value.split(".")[-1]
            return ParseRuleType[rule_type.upper()]
        else:
            return ParseRuleType[value.upper()]

class ParsingPipeline(BaseModel):
    """ Describes how the parser should parse the webpage
    
    Fields:
        name: Optional[str]
        parser: Parser
        parse_rules: List[ParseRule]
    """
    name: Optional[str]
    parser: Parser
    parse_rules: List[ParseRule]
    
    class Config:
        use_enum_values = True
        
    @validator("parser", pre=True)
    def parser_type(cls, value):
        if hasattr(Parser, value):
            return Parser[value.upper()]
        else:
            parser_type = value.split(".")[-1]
            return Parser[parser_type.upper()]


class ScrapeRules(BaseModel):
    """ Describes rules a spider should follow

    Fields:
        keywords: Optional[KeywordRules]
        max_pages: Optional[int]
        max_size: Optional[int]
        max_depth: Optional[int]
        time_range: Optional[TimeRange]
        url_patterns: Optional[List[str]]
        parsing_pipeline: List[ParsingPipeline]
        max_retry: Optional[int] = 1
        max_concurrency: Optional[int] = 50
        request_params: dict = {}
    """
    keywords: Optional[KeywordRules]
    max_pages: Optional[int]
    max_size: Optional[int]
    max_depth: Optional[int]
    time_range: Optional[TimeRange]
    url_patterns: Optional[List[str]]
    api_urls: Optional[List[str]]
    parsing_pipeline: Optional[List[ParsingPipeline]]
    max_retry: Optional[int] = 1
    max_concurrency: Optional[int] = 50
    mode: Optional[str]
    request_params: Optional[dict] = {}



class JobSpecification(BaseModel):
    """ Describes what kind of task a spider should perform

    Fields:
        urls: List[str]
        job_type: JobType
        scrape_rules: ScrapeRules
        data_collection: str = 'test'
        job_collection: str = "jobs"
    """
    urls: List[str]
    job_type: JobType
    scrape_rules: ScrapeRules
    
    class Config:
        use_enum_values = True


class SpiderArgs(BaseModel):
    urls: List[str]
    start_date: Optional[str]
    end_date: Optional[str]
    rules: Optional[ScrapeRules]


class AQISpiderArgs(BaseModel):
    url: str = 'http://tianqihoubao.com/aqi/'
    mode: str = 'update'
    start_date: Optional[str] = '2013-10-01'
    end_date: Optional[str] = '2021-09-01'
    
class CMAWeatherSpiderArgs(BaseModel):
    url: str = 'http://weather.cma.cn'
    


class ResultQuery(BaseModel):
    """ Holds parameters for a result query

    Fields:
        content_type: Optional[ContentType]
        domains: Optional[List[str]]
        keywords: Optional[List[str]]
        start_dt: Optional[datetime]
        end_dt: Optional[datetime]
    """
    content_type: Optional[ContentType]
    domains: Optional[List[str]]
    keywords: Optional[List[str]]
    start_dt: Optional[datetime]
    end_dt: Optional[datetime]


class QueryArgs(BaseModel):
    """ Defines the query parameters for crud operations
    """
    id: Optional[Union[str, int]]
    page: Optional[int] = 1
    page_size: Optional[int] = 10
    field: Optional[str] = ""
    query_expression: Optional[dict]
    start_dt: Optional[Union[date, datetime]]
    end_dt: Optional[Union[date, datetime]]
