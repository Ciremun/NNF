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

DROP TRIGGER IF EXISTS addCartTrigger on users;
DROP TRIGGER IF EXISTS deleteCartTrigger on users;

CREATE TRIGGER addCartTrigger
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION createCart();

CREATE TRIGGER deleteCartTrigger
    BEFORE DELETE ON users
    FOR EACH ROW
    EXECUTE FUNCTION deleteCart();\
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
        sql = f"""\
INSERT INTO \
cart(user_id) VALUES ({user_id})\
"""
        self.cursor.execute(sql)

    @acquireLock
    def addCartProduct(self, cart_id: int, product_id: int):
        sql = f"""\
INSERT INTO \
cartproduct(cart_id, product_id) VALUES ({cart_id}, {product_id})\
"""
        self.cursor.execute(sql)

    @acquireLock
    def addCartProducts(self, ids: list):
        sql = f"""\
INSERT INTO \
cartproduct(cart_id, product_id) VALUES (%s, %s)\
"""
        self.cursor.executemany(sql, ids)

    @acquireLock
    def addUser(self, username: str, displayname: str, password: str, usertype: str):
        sql = f"""\
INSERT INTO \
users(username, displayname, password, usertype) VALUES ('{username}', '{displayname}', '{password}', '{usertype}')\
"""
        self.cursor.execute(sql)

    @acquireLock
    def addSession(self, sid: str, username: str, usertype: str, date: str):
        sql = f"""\
INSERT INTO \
sessions(sid, username, usertype, date) VALUES ('{sid}', '{username}', '{usertype}', '{date}')\
"""
        self.cursor.execute(sql)

    @acquireLock
    def addDailyMenu(self, menu: list):
        sql = f"""\
INSERT INTO \
dailymenu(title, weight, calories, price, link, image_link, section, type, date) \
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)\
"""
        self.cursor.executemany(sql, menu)

    @acquireLock
    def getDailyMenuBySection(self, section: str):
        sql = f"""\
SELECT \
title, weight, calories, price, link, image_link FROM dailymenu \
WHERE section = '{section}'\
"""
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    @acquireLock
    def getUser(self, username):
        sql = f"""\
SELECT \
displayname, password, usertype FROM users WHERE username = '{username}'\
"""
        self.cursor.execute(sql)
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
    def getDailyMenuDate(self):
        sql = """\
SELECT \
date FROM dailymenu\
"""
        self.cursor.execute(sql)
        return self.cursor.fetchone()

    @acquireLock
    def getDailyMenuByType(self, Type: str):
        sql = f"""\
SELECT \
title, weight, calories, price, link, image_link, section FROM dailymenu \
WHERE type = '{Type}'\
"""
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    @acquireLock
    def getDailyMenuByTitlePriceType(self, title: str, price: int, Type: str):
        sql = f"""\
SELECT \
title, price FROM dailymenu \
WHERE title = '{title}' AND price = '{price}' AND type = '{Type}'\
"""
        self.cursor.execute(sql)
        return self.cursor.fetchone()

    @acquireLock
    def getDailyMenuBySectionAndType(self, section: str, Type: str):
        sql = f"""\
SELECT \
id, FROM dailymenu \
WHERE section = '{section}' AND type = '{Type}'\
"""
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    @acquireLock
    def updateSessionDate(self, sid: str, newdate: str):
        sql = f"""\
UPDATE \
sessions SET date = '{newdate}' WHERE sid = '{sid}'\
"""
        self.cursor.execute(sql)

    @acquireLock
    def deleteSession(self, sid: str):
        sql = f"""\
DELETE FROM \
sessions WHERE sid = '{sid}'\
"""
        self.cursor.execute(sql)

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
