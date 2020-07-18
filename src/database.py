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

    def createUsersTable(self):
        sql = """
        CREATE TABLE IF NOT EXISTS users(id serial primary key, username text, displayname text, password text, usertype text)
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
