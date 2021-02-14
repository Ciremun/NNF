from typing import NamedTuple, Optional
from enum import Enum
import datetime

from flask import flash, redirect, make_response, abort, jsonify, request

import src.config as cfg


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
    account_share_id: int


class Cookie(NamedTuple):
    key: str
    value: str


class ResponseType(Enum):
    HTTP = 1
    JSON = 2


class ResponseTypeError(Exception):
    pass


class FormHandler:

    def __init__(self, redirect_url=None, flash_type=None, response_type=ResponseType.HTTP):
        self.redirect_url = redirect_url
        self.flash_type = flash_type
        self.response_type = response_type

    def make_response(self, **data):
        if self.response_type == ResponseType.JSON:
            response_data = jsonify(**data)
        elif self.response_type == ResponseType.HTTP:
            if data.get('message'):
                flash(data['message'], self.flash_type)
            response_data = redirect(self.redirect_url)
        else:
            raise ResponseTypeError(
                f'Unknown ResponseType: {self.response_type}')
        response = make_response(response_data)
        if data.get('cookie'):
            response.set_cookie(
                data['cookie'].key, data['cookie'].value, max_age=2620000, secure=cfg.https)
        return response

    def get_form(self, request: request) -> Optional[dict]:
        data = request.form
        if not data:
            data = request.get_json()
            if not data:
                abort(400)
            self.response_type = ResponseType.JSON
        return data
