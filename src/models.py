from typing import TYPE_CHECKING, NamedTuple, TypedDict
from datetime import datetime, date, tzinfo


class AcfunId(NamedTuple):
    "所有id的基类"

    value: str

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AcfunId):
            return self.value == other.value
        return False


class Uid(AcfunId):
    "Acfun用户id"

    pass


class Vid(AcfunId):
    "Acfun视频id (without ac prefix)"

    pass


class Uploader(NamedTuple):
    "Acfun视频的UP主"

    uid: Uid
    name: str

class PartVideoMetadata(NamedTuple):
    "Acfun分段视频的vid与标题"

    vid: Vid
    title: str

class MultiPartInfo(NamedTuple):
    "Acfun视频的多P信息"

    has_multi_part: bool
    part_list: list[PartVideoMetadata]

class VideoMetadata(TypedDict):
    "Acfun视频的元数据"

    vid: Vid
    title: str
    cover_url: str
    uploader: Uploader
    upload_date: datetime
    multi_p: MultiPartInfo