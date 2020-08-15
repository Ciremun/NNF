import psycopg2
import threading
from src.config import keys


def acquireLock(func):
    def wrapper(self, *args, **kwargs):
        try:
            self.lock.acquire(True)
            return func(self, *args, **kwargs)
        finally:
            self.lock.release()
    return wrapper


class Database(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.start()

        self.conn = psycopg2.connect(
            database=keys['PostgreDatabase'], user=keys['PostgreUser'], password=keys['PostgrePassword'], 
            host=keys['PostgreHost'], port=keys['PostgrePort']
        )
        self.conn.autocommit = True
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()
        self.postgreInit()

    @acquireLock
    def postgreInit(self):
        self.cursor.execute(open('src/sql/tables.sql').read())
        self.cursor.execute(open('src/sql/functions.sql').read())

    @acquireLock
    def addOrder(self, user_id: int, date: str):
        sql = "INSERT INTO orders(user_id, date) VALUES (%s)"
        self.cursor.execute(sql, (user_id,))

    @acquireLock
    def addOrderProduct(self, order_id: int, title: str, price: int, link: str, amount: int):
        sql = """\
INSERT INTO \
orderproduct(order_id, title, price, link, amount) VALUES (%s, %s, %s, %s, %s)\
"""
        self.cursor.execute(sql, (order_id, title, price, link, amount))

    @acquireLock
    def addCartProduct(self, cart_id: int, product_id: int, amount: int, date: float):
        sql = "SELECT addCartProduct(%s, %s, %s, %s)"
        self.cursor.execute(sql, (cart_id, product_id, amount, date))

    @acquireLock
    def addUser(self, username: str, displayname: str, password: str, usertype: str, date: str):
        sql = "SELECT addUser(%s, %s, %s, %s, %s)"
        self.cursor.execute(sql, (username, displayname, password, usertype, date))

    @acquireLock
    def addSession(self, sid: str, username: str, usertype: str, date: str):
        sql = "INSERT INTO sessions(sid, username, usertype, date) VALUES (%s, %s, %s, %s)"
        self.cursor.execute(sql, (sid, username, usertype, date))

    @acquireLock
    def addDailyMenu(self, menu: list):
        sql = """\
INSERT INTO \
dailymenu(title, weight, calories, price, link, image_link, section, type, date) \
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)\
"""
        self.cursor.executemany(sql, menu)

    @acquireLock
    def getUserCartItems(self, username: str):
        sql = """\
SELECT p.title, p.price, p.link, p.type, cp.amount, p.id \
FROM users u \
LEFT JOIN cart ON cart.user_id=u.id \
LEFT JOIN cartproduct cp ON cp.cart_id=cart.id \
INNER JOIN dailymenu p ON p.id=cp.product_id WHERE u.username = %s\
ORDER BY cp.date\
"""
        self.cursor.execute(sql, (username,))
        return self.cursor.fetchall()

    @acquireLock
    def getUserCartSum(self, username: str):
        sql = """\
SELECT SUM(p.price * cp.amount) \
FROM users u \
LEFT JOIN cart ON cart.user_id=u.id \
LEFT JOIN cartproduct cp ON cp.cart_id=cart.id \
LEFT JOIN dailymenu p ON p.id=cp.product_id \
WHERE u.username = %s \
HAVING SUM(p.price)>0 limit 1\
"""
        self.cursor.execute(sql, (username,))
        return self.cursor.fetchone()

    @acquireLock
    def getDailyMenuBySection(self, section: str):
        sql = """\
SELECT \
title, weight, calories, price, link, image_link \
FROM dailymenu \
WHERE section = %s\
"""
        self.cursor.execute(sql, (section,))
        return self.cursor.fetchall()

    @acquireLock
    def getUserCartID(self, username: str):
        sql = """\
SELECT user_id FROM cart \
WHERE user_id = (SELECT id FROM users WHERE username = %s) limit 1\
"""
        self.cursor.execute(sql, (username,))
        return self.cursor.fetchone()

    @acquireLock
    def getUser(self, username: str):
        sql = "SELECT displayname, password, usertype FROM users WHERE username = %s limit 1"
        self.cursor.execute(sql, (username,))
        return self.cursor.fetchone()

    @acquireLock
    def getUserDisplayName(self, username: str):
        sql = "SELECT displayname FROM users WHERE username = %s limit 1"
        self.cursor.execute(sql, (username,))
        return self.cursor.fetchone()

    @acquireLock
    def getSessions(self):
        sql = "SELECT sid, username, usertype, date FROM sessions"
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    @acquireLock
    def getSession(self, SID: str):
        sql = "SELECT username, usertype, date FROM sessions WHERE sid = %s"
        self.cursor.execute(sql, (SID,))
        return self.cursor.fetchone()

    @acquireLock
    def getDailyMenuByType(self, Type: str):
        sql = """\
SELECT \
title, weight, calories, price, link, image_link, section, id FROM dailymenu \
WHERE type = %s\
"""
        self.cursor.execute(sql, (Type,))
        return self.cursor.fetchall()

    @acquireLock
    def getProductID(self, title: str, price: int, Type: str):
        sql = """\
SELECT id FROM dailymenu \
WHERE title = %s AND price = %s AND type = %s limit 1\
"""
        self.cursor.execute(sql, (title, price, Type))
        return self.cursor.fetchone()

    @acquireLock
    def getProductByID(self, product_id: int):
        sql = """\
SELECT id FROM dailymenu \
WHERE id = %s AND (type = 'complex' or type = 'menu')\
"""
        self.cursor.execute(sql, (product_id,))
        return self.cursor.fetchone()

    @acquireLock
    def getComplexItems(self, section: str, Type: str):
        sql = """\
SELECT title, price, link, id FROM dailymenu \
WHERE section = %s AND type = %s\
"""
        self.cursor.execute(sql, (section, Type))
        return self.cursor.fetchall()

    @acquireLock
    def updateSessionDate(self, sid: str, newdate: str):
        sql = "UPDATE sessions SET date = %s WHERE sid = %s"
        self.cursor.execute(sql, (newdate, sid))

    @acquireLock
    def deleteSession(self, sid: str):
        sql = "DELETE FROM sessions WHERE sid = %s"
        self.cursor.execute(sql, (sid,))

    @acquireLock
    def deleteSessions(self, sids: list):
        sql = "DELETE FROM sessions WHERE sid = %s"
        self.cursor.executemany(sql, sids)

    @acquireLock
    def clearDailyMenu(self):
        sql = "DELETE FROM dailymenu"
        self.cursor.execute(sql)

    @acquireLock
    def vacuum(self):
        self.cursor.execute("VACUUM")

    @acquireLock
    def checkDailyMenu(self):
        sql = "SELECT 1 FROM dailymenu limit 1"
        self.cursor.execute(sql)
        return self.cursor.fetchone()
