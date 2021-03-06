import os
import datetime
from threading import Lock
from typing import List, Optional, Tuple

import psycopg2


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
    cursor.execute(open('src/tables.sql').read())


@acquireLock
def addOrder(user_id: int, date: datetime.datetime, order_sum: int):
    sql = "INSERT INTO orders(user_id, date, order_sum) VALUES (%s, %s, %s) RETURNING id"
    cursor.execute(sql, (user_id, date, order_sum))
    return cursor.fetchone()


@acquireLock
def addOrderProducts(order_products: List[Tuple[int, str, int, str, int]]):
    sql = """\
INSERT INTO \
orderproduct(order_id, title, price, link, amount) VALUES (%s, %s, %s, %s, %s)\
"""
    cursor.executemany(sql, order_products)


@acquireLock
def getOrderProducts(user_id: int):
    sql = """\
SELECT op.title, op.price, op.link, op.amount, o.id, o.date, o.order_sum \
FROM orders o JOIN orderproduct op on op.order_id = o.id WHERE \
o.user_id = %s ORDER BY o.date"""
    cursor.execute(sql, (user_id,))
    return cursor.fetchall()


@acquireLock
def addCartProduct(cart_id: int, product_id: int,
                   amount: int, date: datetime.datetime):
    cursor.execute(
        'SELECT EXISTS(SELECT 1 FROM cartproduct WHERE cart_id = %s AND product_id = %s)', (cart_id, product_id))
    if cursor.fetchone()[0]:
        cursor.execute('UPDATE cartproduct SET amount = amount + %s WHERE cart_id = %s AND product_id = %s',
                       (amount, cart_id, product_id))
    else:
        cursor.execute('INSERT INTO cartproduct (cart_id, product_id, amount, date) VALUES (%s, %s, %s, %s)',
                       (cart_id, product_id, amount, date))


@acquireLock
def addUser(username: str, displayname: str, password: str,
            usertype: str, date: datetime.datetime):
    cursor.execute('INSERT INTO users (username, displayname, password, usertype, date) VALUES (%s, %s, %s, %s, %s) RETURNING id',
                   (username, displayname, password, usertype, date))
    user_id = cursor.fetchone()[0]
    cursor.execute('INSERT INTO cart (user_id) VALUES (%s)', (user_id,))
    return user_id


@acquireLock
def addSession(sid: str, date: datetime.datetime,
               user_id: int, asID: Optional[int] = None):
    sql = """\
INSERT INTO sessions(sid, date, user_id, account_share_id) \
VALUES (%s, %s, %s, %s)\
"""
    cursor.execute(sql, (sid, date, user_id, asID))


@acquireLock
def addDailyMenu(menu: List[Tuple[str, str, str, int, str, str, str, str, datetime.datetime]]):
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
    cursor.execute(
        'SELECT EXISTS(SELECT 1 FROM account_share WHERE user_id = %s AND target_user_id = %s)', (user_id, target_user_id))
    if cursor.fetchone()[0]:
        cursor.execute('UPDATE account_share SET duration = %s, date = %s WHERE user_id = %s AND target_user_id = %s',
                       (duration, date, user_id, target_user_id))
    else:
        cursor.execute('INSERT INTO account_share (user_id, target_user_id, duration, date) VALUES (%s, %s, %s, %s)',
                       (user_id, target_user_id, duration, date))


@acquireLock
def addUserFav(user_id: int, product_id: int):
    sql = "INSERT INTO userfav(user_id, product_id) VALUES (%s, %s)"
    cursor.execute(sql, (user_id, product_id))


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
def getUserID(username: str):
    sql = "SELECT id FROM users WHERE username = %s"
    cursor.execute(sql, (username,))
    return cursor.fetchone()


@acquireLock
def getUserIDs():
    sql = "SELECT id FROM users"
    cursor.execute(sql)
    return cursor.fetchall()


@acquireLock
def getSessions():
    sql = "SELECT id, date FROM sessions"
    cursor.execute(sql)
    return cursor.fetchall()


@acquireLock
def getSession(SID: str):
    sql = """\
SELECT u.username, u.displayname, u.usertype, s.date, s.user_id, s.account_share_id \
FROM sessions s JOIN users u ON u.id = s.user_id WHERE sid = %s\
"""
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
SELECT s.user_id, o.displayname, s.target_user_id, t.displayname, s.duration, s.date \
FROM account_share s \
LEFT JOIN users o ON o.id = s.user_id \
LEFT JOIN users t ON t.id = s.target_user_id \
WHERE s.user_id = %s OR s.target_user_id = %s \
ORDER BY s.date DESC\
"""
    cursor.execute(sql, (id_, id_))
    return cursor.fetchall()


@acquireLock
def getAccountShares():
    sql = "SELECT id, duration, date FROM account_share"
    cursor.execute(sql)
    return cursor.fetchall()


@acquireLock
def getUserFavByProductID(user_id: int, product_id: int):
    sql = "SELECT user_id, product_id FROM userfav WHERE user_id = %s AND product_id = %s"
    cursor.execute(sql, (user_id, product_id))
    return cursor.fetchone()


@acquireLock
def updateSessionDate(sid: str, newdate: datetime.datetime):
    sql = "UPDATE sessions SET date = %s WHERE sid = %s"
    cursor.execute(sql, (newdate, sid))


@acquireLock
def updateCartProduct(cart_id: int, product_id: int, amount: int):
    if amount == 0:
        cursor.execute(
            'DELETE FROM cartproduct WHERE cart_id = %s AND product_id = %s', (cart_id, product_id))
    else:
        cursor.execute('UPDATE cartproduct SET amount = %s WHERE cart_id = %s AND product_id = %s',
                       (amount, cart_id, product_id))


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
def deleteUserFav(user_fav: Tuple[int, int]):
    sql = "DELETE FROM userfav WHERE user_id = %s AND product_id = %s"
    cursor.execute(sql, user_fav)


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


conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
conn.autocommit = True
cursor = conn.cursor()
lock = Lock()
postgreInit()
