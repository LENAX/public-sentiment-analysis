from enum import Enum


class JobStatus(str, Enum):
    DONE = 'done'
    WORKING = 'working'
    FAILED = 'failed'


class ContentType(str, Enum):
    WEBPAGE: str = 'webpage'
    IMAGE: str = 'image'
    AUDIO: str = 'audio'
    VIDEO: str = 'video'
