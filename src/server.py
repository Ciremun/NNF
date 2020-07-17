from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask import request
import threading
import src.database

db = src.database.Database()

class FlaskApp(threading.Thread):

    app = Flask(__name__)
    socketio = SocketIO(app)

    def __init__(self):
        threading.Thread.__init__(self)
        self.start()

        db.createLoginTable()

    def run(self):
        self.socketio.run(self.app)

    @staticmethod
    @app.route('/', methods=["GET"])
    def index():
        return render_template('login.html')

    @staticmethod
    @socketio.on('connect_')
    def connect_(message):
        print(message['data'])

    @staticmethod
    @socketio.on('register')
    def register(message):
        db.addUser(message["username"], message["password"])
        print(f'register user {message["username"]}')

app = FlaskApp()
