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

    def createLoginTable(self):
        sql = """
        CREATE TABLE IF NOT EXISTS login(username text, password text)
        """
        self.cursor.execute(sql)

    def addUser(self, username, password):
        sql = f"""
        INSERT INTO login(username, password) VALUES ('{username}', '{password}')
        """
        self.cursor.execute(sql)
