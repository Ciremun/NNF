from typing import NamedTuple
import datetime


class FoodItem:
    def __init__(self, title, weight, calories, price, link, image_link, ID=None):
        self.title = title
        self.weight = weight
        self.calories = calories
        self.price = price
        self.link = link
        self.image_link = image_link
        self.ID = ID

class ShortFoodItem:
    def __init__(self, title, price, link, amount=None, ID=None):
        self.title = title
        self.price = price
        self.link = link
        self.ID = ID
        self.amount = amount

class Session(NamedTuple):
    SID: str
    username: str
    usertype: str
    date: datetime.datetime
    user_id: int
