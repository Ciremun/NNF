from typing import NamedTuple
import datetime

from flask import flash, redirect, make_response


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
    displayname: str
    usertype: str
    date: datetime.datetime
    user_id: int

class Cookie(NamedTuple):
    key: str
    value: str

class FormResponseHandler():

    def __init__(self, redirect_url, message=None, flash_type=None, cookie: Cookie = None):
        self.redirect_url = redirect_url
        self.message = message
        self.flash_type = flash_type
        self.cookie = cookie

    def make_response(self):
        response = make_response(redirect(self.redirect_url))
        if self.message:
            flash(self.message, self.flash_type)
        if self.cookie:
            response.set_cookie(self.cookie.key, self.cookie.value, max_age=2620000)
        return response
