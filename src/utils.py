from math import floor
from typing import Optional, Union
import datetime
import time

import requests

import src.parser as parser
import src.database as db
from .log import logger
from .classes import FoodItem, ShortFoodItem, Session

def new_timecode_explicit(days, hours, minutes, seconds, duration):
    if duration < 1:
        return f'{floor(duration * 1000)}мс'
    timecode = []
    timecode_dict = {'д': days, 'ч': hours, 'м': minutes, 'с': seconds}
    for k, v in timecode_dict.items():
        if v:
            timecode.append(f'{v}{k}')
    return " ".join(timecode)


def seconds_convert(duration):
    """
    Convert seconds to time string
    """
    init_duration = duration
    days = duration // (24 * 3600)
    duration = duration % (24 * 3600)
    hours = duration // 3600
    duration %= 3600
    minutes = duration // 60
    seconds = duration % 60
    days, hours, minutes, seconds = [floor(x) for x in [days, hours, minutes, seconds]]
    return new_timecode_explicit(days, hours, minutes, seconds, init_duration)

def clearDB():
    """
    Delete old sessions, account share, do vacuum.
    """
    while True:
        sessionsToDelete = []
        accountShareToDelete = []
        now = datetime.datetime.now()
        for s in db.getSessions():
            sessionID = s[0]
            sessionDate = s[1]
            if sessionDate + datetime.timedelta(days=30) <= now:
                sessionsToDelete.append((sessionID, ))
        for a in db.getAccountShares():
            asID = a[0]
            asDuration = a[1]
            asDate = a[2]
            if asDuration is not None and asDate + asDuration <= now:
                accountShareToDelete.append((asID,))
        if sessionsToDelete:
            db.deleteSessions(sessionsToDelete)
            sessionsToDelete.clear()
        if accountShareToDelete:
            db.deleteAccountShares(accountShareToDelete)
            accountShareToDelete.clear()
        db.vacuum()
        logger.debug('clearDB')
        time.sleep(60)

def getUserCart(username: str) -> dict:
    cartItems = db.getUserCartItems(username)
    if not cartItems:
        return

    cart = {'complex': {}, 'menu': []}
    for i in cartItems:
        title, price, link, Type, amount, itemID = i[0], i[1], i[2], i[3], i[4], i[5]
        if Type == 'complex':
            cart['complex'][title] = {'foods': [ShortFoodItem(x[0], x[1], x[2], ID=x[3]) 
                                                for x in db.getComplexItems(' '.join((title, f'{price} руб.')), 'complexItem')],
                                      'price': price, 'ID': itemID, 'amount': amount}
        elif Type == 'menu':
            cart['menu'].append(ShortFoodItem(title, price, link, amount=amount, ID=itemID))

    return cart

def updateUserSession(session: Session):
    now = datetime.datetime.now()
    if session.date.day < now.day:
        db.updateSessionDate(session.SID, now)
        logger.info(f'update session {session.username}')

def getSession(SID: str) -> Optional[Session]:
    if not isinstance(SID, str):
        return
    s = db.getSession(SID)
    if s:
        session = Session(SID, s[0], s[1], s[2], s[3], s[4], s[5])
        updateUserSession(session)
        return session

def get_catering():
    catering = {'complex': {}, 'items': {}}
    old_section = None
    for k, v in {'complexItem': catering['complex'], 'menu': catering['items']}.items():
        for i in db.getDailyMenuByType(k):
            section = i[6]
            food_item = FoodItem(i[0], i[1], i[2], i[3], i[4], i[5], ID=i[7])
            if section != old_section:
                if k == 'complexItem':
                    v[section] = {}
                    v[section]['foods'] = []
                    v[section]['foods'].append(food_item)
                    split_ = section.split(' ')
                    product_id = db.getProductID(' '.join(split_[:-2]), int(split_[-2:-1][0]), 'complex')
                    v[section]['ID'] = product_id[0]
                else:
                    v[section] = []
                    v[section].append(food_item)
                old_section = section
                continue
            if k == 'complexItem':
                v[section]['foods'].append(food_item)
            else:
                v[section].append(food_item)
    return catering

def dailyMenuUpdate():
    global catering

    if not db.checkDailyMenu():

        logger.info('update menu')
        catering = parser.getDailyMenu(requests.get("https://www.nam-nyam.ru/catering/").text)

        complexProducts = []
        for section in catering['complex'].keys():
            section = section.split(' ')
            title = ' '.join(section[:-2])
            price = int(section[-2:-1][0])
            complexProducts.append(ShortFoodItem(title, price, 'None'))

        db.clearDailyMenu()
        date = datetime.datetime.now()
        db.addDailyMenu([(v.title, v.weight, v.calories, v.price, v.link, v.image_link, k, 'complexItem', date) \
                            for k, foods in catering['complex'].items() for v in foods] + \
                                [(v.title, v.weight, v.calories, v.price, v.link, v.image_link, k, 'menu', date) \
                                    for k, foods in catering['items'].items() for v in foods] + \
                                        [(p.title, 'None', 'None', p.price, 'None', 'None', 'None', 'complex', date) \
                                            for p in complexProducts])

def getSessionAccountShare(session: Session, userinfo: dict) -> dict:
    account_share = db.getAccountShareByID(session.user_id)
    if account_share:
        available, shared_to = {}, {}
        for i in account_share:
            user_id, user, target_user_id, target_user, \
                s_Duration, s_Date = i[0], i[1], i[2], i[3], i[4], i[5]
            if user_id == session.user_id:
                if s_Duration is None:
                    duration = 'Бессрочно'
                else:
                    now = datetime.datetime.now()
                    expiration_date = s_Date + s_Duration
                    if expiration_date <= now:
                        duration = 'Истек'
                    else:
                        seconds_left = (expiration_date - now).total_seconds()
                        duration = seconds_convert(seconds_left)
                shared_to[target_user] = {'id': target_user_id, 
                                          'duration': duration}
            else:
                available[user] = user_id
        userinfo['account_share'] = {
            'available': available,
            'shared_to': shared_to
        }
    return userinfo
    