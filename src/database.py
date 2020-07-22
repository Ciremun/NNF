import psycopg2
import threading
from src.config import keys

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

        self.createUsersTable()
        self.createSessionsTable()
        self.createDailyMenuTable()

    def createUsersTable(self):
        sql = """\
CREATE TABLE IF NOT EXISTS \
users(id serial primary key, username text, displayname text, password text, usertype text)\
"""
        self.cursor.execute(sql)

    def createSessionsTable(self):
        sql = """\
CREATE TABLE IF NOT EXISTS \
sessions(id serial primary key, sid text, username text, usertype text, date date)\
"""
        self.cursor.execute(sql)

    def createDailyMenuTable(self):
        sql = """\
CREATE TABLE IF NOT EXISTS \
dailymenu(id serial primary key, title text, weight text, calories text, price text, \
link text, image_link text, section text, type text, date date)\
"""
        self.cursor.execute(sql)

    def addUser(self, username, displayname, password, usertype):
        sql = f"""\
INSERT INTO \
users(username, displayname, password, usertype) VALUES ('{username}', '{displayname}', '{password}', '{usertype}')\
"""
        self.cursor.execute(sql)

    def addSession(self, sid, username, usertype, date):
        sql = f"""\
INSERT INTO \
sessions(sid, username, usertype, date) VALUES ('{sid}', '{username}', '{usertype}', '{date}')\
"""
        self.cursor.execute(sql)

    def addDailyMenu(self, menu: list):
        sql = f"""\
INSERT INTO \
dailymenu(title, weight, calories, price, link, image_link, section, type, date) \
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)\
"""
        self.cursor.executemany(sql, menu)

    def getUser(self, username):
        sql = f"""\
SELECT \
displayname, password, usertype FROM users WHERE username = '{username}'\
"""
        self.cursor.execute(sql)
        return self.cursor.fetchone()

    def getSessions(self):
        sql = """\
SELECT \
sid, username, usertype, date FROM sessions\
"""
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def getDailyMenuDate(self):
        sql = """\
SELECT \
date FROM dailymenu\
"""
        self.cursor.execute(sql)
        return self.cursor.fetchone()

    def getDailyMenu(self, Type):
        sql = f"""\
SELECT \
title, weight, calories, price, link, image_link, section FROM dailymenu \
WHERE type = '{Type}'\
"""
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def updateSessionDate(self, sid, newdate):
        sql = f"""\
UPDATE \
sessions SET date = '{newdate}' WHERE sid = '{sid}'\
"""
        self.cursor.execute(sql)

    def deleteSession(self, sid: str):
        sql = f"""\
DELETE FROM \
sessions WHERE sid = '{sid}'\
"""
        self.cursor.execute(sql)

    def deleteSessions(self, sids: list):
        sql = """\
DELETE FROM \
sessions WHERE sid = %s\
"""
        self.cursor.executemany(sql, sids)

    def clearDailyMenu(self):
        sql = """\
DELETE FROM dailymenu\
"""
        self.cursor.execute(sql)
