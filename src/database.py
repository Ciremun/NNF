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
        self.createComplexProductTable()

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
dailymenu(id serial primary key, title text, weight text, calories text, price text, \
link text, image_link text, section text, type text, date date)\
"""
        self.cursor.execute(sql)

    @acquireLock
    def createComplexProductTable(self):
        sql = """\
CREATE TABLE IF NOT EXISTS \
complexproduct(id serial primary key, title text, price text)\
"""
        self.cursor.execute(sql)

    @acquireLock
    def addUser(self, username, displayname, password, usertype):
        sql = f"""\
INSERT INTO \
users(username, displayname, password, usertype) VALUES ('{username}', '{displayname}', '{password}', '{usertype}')\
"""
        self.cursor.execute(sql)

    @acquireLock
    def addSession(self, sid, username, usertype, date):
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
    def addComplexProducts(self, products: list):
        sql = f"""\
INSERT INTO \
complexproduct(title, price) VALUES (%s, %s)\
"""
        self.cursor.executemany(sql, products)

    @acquireLock
    def getComplexProduct(self, title, price):
        sql = f"""\
SELECT \
title, price FROM complexproduct \
WHERE title = '{title}' and price = '{price}'\
"""
        self.cursor.execute(sql)
        return self.cursor.fetchone()

    @acquireLock
    def getDailyMenuBySection(self, section):
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
    def getDailyMenuByType(self, Type):
        sql = f"""\
SELECT \
title, weight, calories, price, link, image_link, section FROM dailymenu \
WHERE type = '{Type}'\
"""
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    @acquireLock
    def updateSessionDate(self, sid, newdate):
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
    def clearComplexProducts(self):
        sql = """\
DELETE FROM complexproduct\
"""
        self.cursor.execute(sql)
