import psycopg2
import threading

class Database(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

        self.conn = psycopg2.connect(
            database="test", user='postgres', password='admin', host='127.0.0.1', port='5432'
        )
        self.conn.autocommit = True
        self.cursor = self.conn.cursor()

        self.start()

    def createTable(self):
        pass

db = Database()

db.createTable()