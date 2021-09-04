from pydantic import BaseModel
from typing import List, Any, Union, Dict


class ParseResult(BaseModel):
    """ Defines the parse result from a parser
    
    Fields:
        field_name: str,
        field_value: str  
    """
    name: str
    # value: Union[str, List[str], Dict[str, Any], Any]
    value: Any

    def __hash__(self):
        return hash(self.__repr__())

    def value_to_dict(self) -> dict:
        return {key: self.value[key].value
                for key in self.value}
