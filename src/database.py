import psycopg2
import threading
from src.config import config

class Database(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.start()

        self.conn = psycopg2.connect(
            database=config['database'], user=config['user'], password=config['password'], 
            host=config['host'], port=config['port']
        )
        self.conn.autocommit = True
        self.cursor = self.conn.cursor()

    def createUsersTable(self):
        sql = """
        CREATE TABLE IF NOT EXISTS users(id serial primary key, username text, displayname text, password text)
        """
        self.cursor.execute(sql)

    def addUser(self, username, displayname, password):
        sql = f"""
        INSERT INTO users(username, displayname, password) VALUES ('{username}', '{displayname}', '{password}')
        """
        self.cursor.execute(sql)

    def getUser(self, username):
        sql = f"""
        SELECT username FROM users WHERE username = '{username}'
        """
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def getUserPasswordHash(self, username):
        sql = f"""
        SELECT password FROM users WHERE username = '{username}'
        """
        self.cursor.execute(sql)
        return self.cursor.fetchall()
