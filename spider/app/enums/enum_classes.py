from enum import Enum


class JobState(str, Enum):
    PENDING = 'pending'
    DONE = 'done'
    WORKING = 'working'
    FAILED = 'failed'


class ContentType(str, Enum):
    WEBPAGE: str = 'webpage'
    IMAGE: str = 'image'
    AUDIO: str = 'audio'
    VIDEO: str = 'video'


class JobType(str, Enum):
    """ Job types supported by spiders

    BASIC_PAGE_SCRAPING: only scrape the provided urls and return the html of those urls,
    SEARCH_RESULT_AGGREGATION: perform searches on search engines or general search page and retrieve their results,
    WEB_CRAWLING: Start from seed urls, follow all links available.
    """
    BASIC_PAGE_SCRAPING: str = 'basic_page_scraping'
    SEARCH_RESULT_AGGREGATION: str = 'search_result_aggregation'
    # WEB_CRAWLING: str = 'web_crawling'