import psycopg2
import threading
from src.config import config

class Database(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.start()

        self.conn = psycopg2.connect(
            database=config['PostgreDatabase'], user=config['PostgreUser'], password=config['PostgrePassword'], 
            host=config['PostgreHost'], port=config['PostgrePort']
        )
        self.conn.autocommit = True
        self.cursor = self.conn.cursor()

        self.createUsersTable()
        self.createSessionsTable()

    def createUsersTable(self):
        sql = """
        CREATE TABLE IF NOT EXISTS users(id serial primary key, username text, displayname text, password text, usertype text)
        """
        self.cursor.execute(sql)

    def createSessionsTable(self):
        sql = """
        CREATE TABLE IF NOT EXISTS sessions(id serial primary key, sid text, username text, usertype text, date text)
        """
        self.cursor.execute(sql)

    def addUser(self, username, displayname, password, usertype):
        sql = f"""
        INSERT INTO users(username, displayname, password, usertype) VALUES ('{username}', '{displayname}', '{password}', '{usertype}')
        """
        self.cursor.execute(sql)

    def getUser(self, username):
        sql = f"""
        SELECT displayname, password, usertype FROM users WHERE username = '{username}'
        """
        self.cursor.execute(sql)
        return self.cursor.fetchone()

    def addSession(self, sid, username, usertype, date):
        sql = f"""
        INSERT INTO sessions(sid, username, usertype, date) VALUES ('{sid}', '{username}', '{usertype}', '{date}')
        """
        self.cursor.execute(sql)

    def updateSessionDate(self, sid, newdate):
        sql = f"""
        UPDATE sessions SET date = '{newdate}' WHERE sid = '{sid}'
        """
        self.cursor.execute(sql)

    def deleteSession(self, sid: str):
        sql = f"""
        DELETE FROM sessions WHERE sid = '{sid}'
        """
        self.cursor.execute(sql)

    def deleteSessions(self, sids: list):
        sql = """
        DELETE FROM sessions WHERE sid = %s
        """
        self.cursor.executemany(sql, sids)

    def getSessions(self):
        sql = f"""
        SELECT sid, username, usertype, date FROM sessions
        """
        self.cursor.execute(sql)
        return self.cursor.fetchall()
