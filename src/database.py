import datetime
from threading import Lock
from typing import List, Optional, Tuple

import psycopg2

from .config import keys


def acquireLock(func):
    def wrapper(*args, **kwargs):
        try:
            lock.acquire(True)
            return func(*args, **kwargs)
        finally:
            lock.release()
    return wrapper

@acquireLock
def postgreInit():
    cursor.execute(open('src/sql/tables.sql').read())
    cursor.execute(open('src/sql/functions.sql').read())

@acquireLock
def addOrder(user_id: int, date: str):
    sql = "INSERT INTO orders(user_id, date) VALUES (%s)"
    cursor.execute(sql, (user_id,))

@acquireLock
def addOrderProduct(order_id: int, title: str, price: int, link: str, amount: int):
    sql = """\
INSERT INTO \
orderproduct(order_id, title, price, link, amount) VALUES (%s, %s, %s, %s, %s)\
"""
    cursor.execute(sql, (order_id, title, price, link, amount))

@acquireLock
def addCartProduct(cart_id: int, product_id: int, amount: int, date: datetime.datetime):
    sql = "SELECT addCartProduct(%s, %s, %s, %s)"
    cursor.execute(sql, (cart_id, product_id, amount, date))

@acquireLock
def addUser(username: str, displayname: str, password: str, usertype: str, date: datetime.datetime):
    sql = "SELECT addUser(%s, %s, %s, %s, %s)"
    cursor.execute(sql, (username, displayname, password, usertype, date))
    return cursor.fetchone()

@acquireLock
def addSession(sid: str, username: str, usertype: str, 
               date: datetime.datetime, user_id: int, 
               asID: Optional[int] = None):
    sql = """\
INSERT INTO sessions(sid, username, usertype, date, user_id, account_share_id) \
VALUES (%s, %s, %s, %s, %s, %s)\
"""
    cursor.execute(sql, (sid, username, usertype, date, user_id, asID))

@acquireLock
def addDailyMenu(menu: List[tuple]):
    sql = """\
INSERT INTO \
dailymenu(title, weight, calories, price, link, image_link, section, type, date) \
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)\
"""
    cursor.executemany(sql, menu)

@acquireLock
def addAccountShare(user_id: int, target_user_id: int, 
                    duration: Optional[datetime.timedelta], 
                    date: Optional[datetime.datetime]):
    sql = "SELECT addAccountShare(%s, %s, %s, %s)"
    cursor.execute(sql, (user_id, target_user_id, duration, date))

@acquireLock
def getUserCartItems(username: str):
    sql = """\
SELECT p.title, p.price, p.link, p.type, cp.amount, p.id \
FROM users u \
LEFT JOIN cart ON cart.user_id=u.id \
LEFT JOIN cartproduct cp ON cp.cart_id=cart.id \
INNER JOIN dailymenu p ON p.id=cp.product_id WHERE u.username = %s\
ORDER BY cp.date\
"""
    cursor.execute(sql, (username,))
    return cursor.fetchall()

@acquireLock
def getUserCartSum(username: str):
    sql = """\
SELECT SUM(p.price * cp.amount) \
FROM users u \
LEFT JOIN cart ON cart.user_id=u.id \
LEFT JOIN cartproduct cp ON cp.cart_id=cart.id \
LEFT JOIN dailymenu p ON p.id=cp.product_id \
WHERE u.username = %s \
HAVING SUM(p.price)>0 limit 1\
"""
    cursor.execute(sql, (username,))
    return cursor.fetchone()

@acquireLock
def getDailyMenuBySection(section: str):
    sql = """\
SELECT \
title, weight, calories, price, link, image_link \
FROM dailymenu \
WHERE section = %s\
"""
    cursor.execute(sql, (section,))
    return cursor.fetchall()

@acquireLock
def getUserCartID(username: str):
    sql = """\
SELECT user_id FROM cart \
WHERE user_id = (SELECT id FROM users WHERE username = %s)\
"""
    cursor.execute(sql, (username,))
    return cursor.fetchone()

@acquireLock
def getUser(username: str):
    sql = "SELECT displayname, password, usertype, id FROM users WHERE username = %s"
    cursor.execute(sql, (username,))
    return cursor.fetchone()

@acquireLock
def getUserByID(user_id: int):
    sql = "SELECT username, displayname, usertype FROM users WHERE id = %s"
    cursor.execute(sql, (user_id,))
    return cursor.fetchone()

@acquireLock
def getUserDisplayName(username: str):
    sql = "SELECT displayname FROM users WHERE username = %s"
    cursor.execute(sql, (username,))
    return cursor.fetchone()

@acquireLock
def getUserID(username: str):
    sql = "SELECT id FROM users WHERE username = %s"
    cursor.execute(sql, (username,))
    return cursor.fetchone()

@acquireLock
def getSessions():
    sql = "SELECT id, date FROM sessions"
    cursor.execute(sql)
    return cursor.fetchall()

@acquireLock
def getSession(SID: str):
    sql = "SELECT username, usertype, date, user_id FROM sessions WHERE sid = %s"
    cursor.execute(sql, (SID,))
    return cursor.fetchone()

@acquireLock
def getDailyMenuByType(Type: str):
    sql = """\
SELECT \
title, weight, calories, price, link, image_link, section, id FROM dailymenu \
WHERE type = %s\
"""
    cursor.execute(sql, (Type,))
    return cursor.fetchall()

@acquireLock
def getProductID(title: str, price: int, Type: str):
    sql = """\
SELECT id FROM dailymenu \
WHERE title = %s AND price = %s AND type = %s\
"""
    cursor.execute(sql, (title, price, Type))
    return cursor.fetchone()

@acquireLock
def getProductByID(product_id: int):
    sql = """\
SELECT id FROM dailymenu \
WHERE id = %s AND (type = 'complex' or type = 'menu')\
"""
    cursor.execute(sql, (product_id,))
    return cursor.fetchone()

@acquireLock
def getComplexItems(section: str, Type: str):
    sql = """\
SELECT title, price, link, id FROM dailymenu \
WHERE section = %s AND type = %s\
"""
    cursor.execute(sql, (section, Type))
    return cursor.fetchall()

@acquireLock
def verifyAccountShare(user_id: int, target_user_id: int):
    sql = "SELECT duration, date, id FROM account_share WHERE user_id = %s AND target_user_id = %s"
    cursor.execute(sql, (user_id, target_user_id))
    return cursor.fetchone()

@acquireLock
def getAccountShareByID(id_: int):
    sql = """\
SELECT s.user_id, o.displayname, s.target_user_id, t.displayname \
FROM account_share s \
LEFT JOIN users o ON o.id = s.user_id \
LEFT JOIN users t ON t.id = s.target_user_id \
WHERE s.user_id = %s OR s.target_user_id = %s
"""
    cursor.execute(sql, (id_, id_))
    return cursor.fetchall()

@acquireLock
def getAccountShares():
    sql = "SELECT id, duration, date FROM account_share"
    cursor.execute(sql)
    return cursor.fetchall()

@acquireLock
def updateSessionDate(sid: str, newdate: datetime.datetime):
    sql = "UPDATE sessions SET date = %s WHERE sid = %s"
    cursor.execute(sql, (newdate, sid))

@acquireLock
def updateCartProduct(cart_id: int, product_id: int, amount: int):
    sql = "SELECT updateCartProduct(%s, %s, %s)"
    cursor.execute(sql, (cart_id, product_id, amount))

@acquireLock
def clearUserCart(cart_id: int):
    sql = "DELETE FROM cartproduct WHERE cart_id = %s"
    cursor.execute(sql, (cart_id,))

@acquireLock
def deleteAccountShare(user_id: int, target_user_id: int):
    sql = "DELETE FROM account_share WHERE user_id = %s AND target_user_id = %s"
    cursor.execute(sql, (user_id, target_user_id))

@acquireLock
def deleteAccountShares(IDs: List[Tuple[int]]):
    sql = "DELETE FROM account_share WHERE id = %s"
    cursor.executemany(sql, IDs)

@acquireLock
def deleteSession(sid: str):
    sql = "DELETE FROM sessions WHERE sid = %s"
    cursor.execute(sql, (sid,))

@acquireLock
def deleteSessions(IDs: List[Tuple[int]]):
    sql = "DELETE FROM sessions WHERE id = %s"
    cursor.executemany(sql, IDs)

@acquireLock
def clearDailyMenu():
    sql = "DELETE FROM dailymenu"
    cursor.execute(sql)

@acquireLock
def checkDailyMenu():
    sql = "SELECT 1 FROM dailymenu limit 1"
    cursor.execute(sql)
    return cursor.fetchone()

@acquireLock
def vacuum():
    cursor.execute("VACUUM")

conn = psycopg2.connect(
            database=keys['PostgreDatabase'], user=keys['PostgreUser'], password=keys['PostgrePassword'], 
            host=keys['PostgreHost'], port=keys['PostgrePort']
        )
conn.autocommit = True
cursor = conn.cursor()
lock = Lock()
postgreInit()
