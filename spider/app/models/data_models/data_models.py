
from pydantic import BaseModel
from typing import Optional, List, Any, Union, AnyStr, Dict
from datetime import datetime, timedelta
from ..request_models import (
    JobSpecification
)
from ...enums import JobState, ParseRuleType
from ...utils.regex_patterns import domain_pattern

class DataModel(BaseModel):
    pass

class RequestHeader(BaseModel):
    """ Builds a request header for a spider

    Fields:
        accept: str
        authorization: Optional[str]
        user_agent: str
        cookie: Union[dict, str]
    """
    accept: Optional[str]
    authorization: Optional[str] = ""
    user_agent: str
    cookie: Union[str, dict] = ""


class ParseRule(BaseModel):
    """ Defines the parse rule for a parser

    Fields:
        field_name: str,
        rule: str,
        rule_type: ParseRuleType        
    """
    field_name: Optional[str]
    rule: str
    rule_type: ParseRuleType
    is_link: Optional[bool] = False
