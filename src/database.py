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

        self.createUsersTable()
        self.createSessionsTable()
        self.createDailyMenuTable()
        self.createCartTable()
        self.createCartProductTable()
        self.createTriggers()

    @acquireLock
    def createTriggers(self):
        """
        Create cart on user signup.
        Delete cart on user delete.
        """
        sql = """\
CREATE OR REPLACE FUNCTION createCart()
    RETURNS TRIGGER AS $$
    BEGIN
        INSERT INTO cart(user_id)
        VALUES ((SELECT id FROM users WHERE username = NEW.username));
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION deleteCart()
    RETURNS TRIGGER AS $$
    BEGIN
        DELETE FROM cart
        WHERE user_id = (SELECT id FROM users WHERE username = OLD.username);
        RETURN OLD;
    END;
    $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION deleteCartProduct()
    RETURNS TRIGGER AS $$
    BEGIN
        DELETE FROM cartproduct WHERE product_id = OLD.id;
        RETURN OLD;
    END;
    $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS addCartTrigger on users;
DROP TRIGGER IF EXISTS deleteCartTrigger on users;
DROP TRIGGER IF EXISTS deleteCartProductTrigger on dailymenu;

CREATE TRIGGER addCartTrigger
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION createCart();

CREATE TRIGGER deleteCartTrigger
    BEFORE DELETE ON users
    FOR EACH ROW
    EXECUTE FUNCTION deleteCart();

CREATE TRIGGER deleteCartProductTrigger
    BEFORE DELETE ON dailymenu
    FOR EACH ROW
    EXECUTE FUNCTION deleteCartProduct();\
"""
        self.cursor.execute(sql)

    @acquireLock
    def createUsersTable(self):
        sql = """\
CREATE TABLE IF NOT EXISTS \
users(id serial primary key, username text, displayname text, password text, usertype text)\
"""
        self.cursor.execute(sql)

    @acquireLock
    def createSessionsTable(self):
        sql = """\
CREATE TABLE IF NOT EXISTS \
sessions(id serial primary key, sid text, username text, usertype text, date date)\
"""
        self.cursor.execute(sql)

    @acquireLock
    def createDailyMenuTable(self):
        sql = """\
CREATE TABLE IF NOT EXISTS \
dailymenu(id serial primary key, title text, weight text, calories text, price integer, \
link text, image_link text, section text, type text, date date)\
"""
        self.cursor.execute(sql)

    @acquireLock
    def createCartTable(self):
        sql = """\
CREATE TABLE IF NOT EXISTS \
cart(user_id integer references users(id), id serial primary key)\
"""
        self.cursor.execute(sql)

    @acquireLock
    def createCartProductTable(self):
        sql = """\
CREATE TABLE IF NOT EXISTS \
cartproduct(cart_id integer references cart(id), \
product_id integer references dailymenu(id), id serial primary key)\
"""
        self.cursor.execute(sql)

    @acquireLock
    def addCart(self, user_id: int):
        sql = """\
INSERT INTO \
cart(user_id) VALUES (%s)\
"""
        self.cursor.execute(sql, (user_id,))

    @acquireLock
    def addCartProduct(self, cart_id: int, product_id: int):
        sql = """\
INSERT INTO \
cartproduct(cart_id, product_id) VALUES (%s, %s)\
"""
        self.cursor.execute(sql, (cart_id, product_id))

    @acquireLock
    def addCartProducts(self, ids: list):
        sql = """\
INSERT INTO \
cartproduct(cart_id, product_id) VALUES (%s, %s)\
"""
        self.cursor.executemany(sql, ids)

    @acquireLock
    def addUser(self, username: str, displayname: str, password: str, usertype: str):
        sql = """\
INSERT INTO \
users(username, displayname, password, usertype) VALUES (%s, %s, %s, %s)\
"""
        self.cursor.execute(sql, (username, displayname, password, usertype))

    @acquireLock
    def addSession(self, sid: str, username: str, usertype: str, date: str):
        sql = """\
INSERT INTO \
sessions(sid, username, usertype, date) VALUES (%s, %s, %s, %s)\
"""
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
SELECT p.title, p.price, p.link, p.type, COUNT(p.title) \
FROM users u LEFT JOIN cart ON cart.user_id=u.id \
LEFT JOIN cartproduct cp ON cp.cart_id=cart.id \
LEFT JOIN dailymenu p ON p.id=cp.product_id \
WHERE u.username = %s \
GROUP by p.title, p.price, p.link, p.type \
HAVING COUNT(p.title) > 0\
"""
        self.cursor.execute(sql, (username,))
        return self.cursor.fetchall()

    @acquireLock
    def getUserCartSum(self, username: str):
        sql = """\
SELECT sum(p.price) \
FROM users u \
LEFT JOIN cart ON cart.user_id=u.id \
LEFT JOIN cartproduct cp ON cp.cart_id=cart.id \
LEFT JOIN dailymenu p ON p.id=cp.product_id \
WHERE u.username = %s\
"""
        self.cursor.execute(sql, (username,))
        return self.cursor.fetchone()

    @acquireLock
    def getDailyMenuBySection(self, section: str):
        sql = """\
SELECT \
title, weight, calories, price, link, image_link FROM dailymenu \
WHERE section = %s\
"""
        self.cursor.execute(sql, (section,))
        return self.cursor.fetchall()

    @acquireLock
    def getUserCartID(self, username: str):
        sql = """\
SELECT user_id FROM cart WHERE user_id = (SELECT id FROM users WHERE username = %s)\
"""
        self.cursor.execute(sql, (username,))
        return self.cursor.fetchone()

    @acquireLock
    def getUser(self, username: str):
        sql = """\
SELECT \
displayname, password, usertype FROM users WHERE username = %s\
"""
        self.cursor.execute(sql, (username,))
        return self.cursor.fetchone()

    @acquireLock
    def getUserDisplayName(self, username: str):
        sql = """\
SELECT \
displayname FROM users WHERE username = %s\
"""
        self.cursor.execute(sql, (username,))
        return self.cursor.fetchone()

    @acquireLock
    def getSessions(self):
        sql = """\
SELECT \
sid, username, usertype, date FROM sessions\
"""
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    @acquireLock
    def getDailyMenuID(self):
        sql = """\
SELECT \
id FROM dailymenu\
"""
        self.cursor.execute(sql)
        return self.cursor.fetchone()

    @acquireLock
    def getDailyMenuByType(self, Type: str):
        sql = """\
SELECT \
title, weight, calories, price, link, image_link, section FROM dailymenu \
WHERE type = %s\
"""
        self.cursor.execute(sql, (Type,))
        return self.cursor.fetchall()

    @acquireLock
    def getProductID(self, title: str, price: int, Type: str):
        sql = """\
SELECT \
id FROM dailymenu \
WHERE title = %s AND price = %s AND type = %s\
"""
        self.cursor.execute(sql, (title, price, Type))
        return self.cursor.fetchone()

    @acquireLock
    def getComplexItems(self, section: str, Type: str):
        sql = """\
SELECT \
title, price, link FROM dailymenu \
WHERE section = %s AND type = %s\
"""
        self.cursor.execute(sql, (section, Type))
        return self.cursor.fetchall()

    @acquireLock
    def updateSessionDate(self, sid: str, newdate: str):
        sql = """\
UPDATE \
sessions SET date = %s WHERE sid = %s\
"""
        self.cursor.execute(sql, (newdate, sid))

    @acquireLock
    def deleteSession(self, sid: str):
        sql = """\
DELETE FROM \
sessions WHERE sid = %s\
"""
        self.cursor.execute(sql, (sid,))

    @acquireLock
    def deleteSessions(self, sids: list):
        sql = """\
DELETE FROM \
sessions WHERE sid = %s\
"""
        self.cursor.executemany(sql, sids)

    @acquireLock
    def clearDailyMenu(self):
        sql = """\
DELETE FROM dailymenu\
"""
        self.cursor.execute(sql)

    @acquireLock
    def vacuum(self):
        self.cursor.execute("VACUUM")
