from typing import NamedTuple
import datetime

class Session(NamedTuple):
    SID: str
    username: str
    usertype: str
    date: datetime.date
