from enum import Enum


class JobState(str, Enum):
    PENDING = 'pending'
    DONE = 'done'
    WORKING = 'working'
    PAUSED = 'paused'
    CENCELLED = 'cancelled'
    STOPPED = 'stopped'
    RESUMED = 'resumed'
    FAILED = 'failed'


class RequestStatus(str, Enum):
    """ Maps common HTTP status codes to their corresponding meanings
    """
    CREATED = 'created'
    WAITING = 'waiting'
    SUCCESS = 'success'
    TIMEOUT = 'timeout'
    CLIENT_ERROR = 'client_error'
    SERVER_ERROR = 'server_error'
    BAD_REQUEST = 'bad_request'
    UNAUTHORIZED = 'unauthorized'
    FORBIDDEN = 'forbidden'
    NOT_FOUND = 'not_found'
    INTERNAL_SERVER_ERROR = 'internal_server_error'
    TOO_MANY_REQUESTS = 'too_many_requests'
    REDIRECTED = 'redirected'

    @classmethod
    def from_status_code(cls, status_code: int):
        """ Convert a status code to its string representation """
        # checks whether status code is between 200 and 206, but
        # range is exclusive on the right hand side
        if 200 <= status_code <= 206:
            return cls.SUCCESS
        elif 300 <= status_code <= 309:
            return cls.REDIRECTED
        elif status_code == 400:
            return cls.BAD_REQUEST
        elif status_code == 401:
            return cls.UNAUTHORIZED
        elif status_code == 403:
            return cls.FORBIDDEN
        elif status_code == 404:
            return cls.NOT_FOUND
        elif status_code == 429:
            return cls.TOO_MANY_REQUESTS
        elif 405 <= status_code <= 452:
            return cls.CLIENT_ERROR
        elif status_code == 429:
            return cls.TOO_MANY_REQUESTS
        elif status_code == 500:
            return cls.INTERNAL_SERVER_ERROR
        elif 501 <= status_code <= 511:
            return cls.SERVER_ERROR
        

class ParseRuleType(str, Enum):
    """ Parse rule types supported by parsers 
    
    One of:
        XPATH,
        CSS_SELECTOR,
        REGEX
    """
    XPATH: str = 'xpath'
    CSS_SELECTOR: str = 'css_selector'
    REGEX: str = 'regex'
    CLASS_NAME: str = 'class_name'
    ELEMENT_ID: str = 'element_id'
    TEXT_CONTENT: str = 'text_content'


class Parser(str, Enum):
    """ supported parser types

    One of:
        HTML_PARSER,
        LINK_PARSER,
        DATETIME_PARSER
    """
    HTML_PARSER = 'html_parser'
    GENERAL_NEWS_PARSER = 'general_news_parser'
    LIST_ITEM_PARSER = 'list_item_parser'
    LINK_PARSER = 'link_parser'
    DATETIME_PARSER = 'datetime_parser'

class ContentType(str, Enum):
    WEBPAGE: str = 'webpage'
    IMAGE: str = 'image'
    AUDIO: str = 'audio'
    VIDEO: str = 'video'


class JobType(str, Enum):
    """ Job types supported by spiders

    COVID_REPORT: str = 'baidu_covid_report'
    BAIDU_NEWS_SCRAPING: str = 'baidu_news_scraping'
    WEATHER_REPORT: str = 'weather_report'
    AIR_QUALITY_REPORT: str = 'air_quality'
    """
    # BASIC_PAGE_SCRAPING: str = 'basic_page_scraping'
    COVID_REPORT: str = 'baidu_covid_report'
    BAIDU_NEWS_SCRAPING: str = 'baidu_news_scraping'
    WEATHER_REPORT: str = 'weather_report'
    AIR_QUALITY_REPORT: str = 'air_quality'
