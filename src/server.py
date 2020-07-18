from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask import request, redirect, Response
import threading
import json
import time
import logging
import src.database
from src.salt import hash_password, verify_password
from src.config import config

db = src.database.Database()
sessionSecret = json.load(open('keys.json'))['sessionSecret']
sessions = {}

class FlaskApp(threading.Thread):

    app = Flask(__name__)
    socketio = SocketIO(app)

    if not config['flaskLogging']:
        log = logging.getLogger('werkzeug').disabled = True

    def __init__(self):
        threading.Thread.__init__(self)
        self.start()

        db.createUsersTable()

    def run(self):
        self.socketio.run(self.app, host='0.0.0.0', port=config['flaskPort'])

    @staticmethod
    @app.route('/')
    def index():
        return redirect('/profile', code=302)

    @staticmethod
    @app.route('/login')
    def login():
        return render_template('login.html', host=config['flaskHost'], port=config['flaskPort'], version=round(time.time()))

    @staticmethod
    @app.route('/profile')
    def autoprofile():
        username = sessions.get(request.cookies.get("SID"))
        if username:
            displayname = db.getUserDisplayname(username)
            if not displayname:
                return Response("User not found", status=404)
            return render_template('userprofile.html', username=username, displayname=displayname[0][0], 
                                    host=config['flaskHost'], port=config['flaskPort'], version=round(time.time()))
        return redirect('/login', code=302)

    @staticmethod
    @app.route('/u/<username>')
    def linkprofile(username):
        username = username.lower()
        displayname = db.getUserDisplayname(username)
        if not displayname:
            return Response("User not found", status=404)
        if sessions.get(request.cookies["SID"]) == username:
            return render_template('userprofile.html', username=username, displayname=displayname[0][0], 
                                    host=config['flaskHost'], port=config['flaskPort'], version=round(time.time()))
        return Response("401 Unauthorized", status=401)

    @staticmethod
    @socketio.on('login')
    def onlogin(message):
        user = message['username']
        password = message['password']
        hashed_pwd = db.getUserPasswordHash(user)
        if hashed_pwd:
            hashed_pwd = hashed_pwd[0][0]
            if verify_password(hashed_pwd, password):
                SID = hash_password(sessionSecret)
                sessions[SID] = user
                emit('loginSuccess', {'username': user, 'SID': SID})
                print(f'login user {user}')
            else:
                emit('loginFail')
                print(f'failed login user {user}')
            return
        hashed_pwd = hash_password(password)
        db.addUser(user, message["displayname"], hashed_pwd)
        SID = hash_password(sessionSecret)
        sessions[SID] = user
        emit('loginSuccess', {'username': user, 'SID': SID})
        print(f'register user {user}')

    @staticmethod
    @socketio.on('logout')
    def onlogout(message):
        try:
            del sessions[message['SID']]
            emit('logout')
        except KeyError:
            return

    @staticmethod
    @socketio.on('clearSID')
    def onclearSID(message):
        try:
            del sessions[message['SID']]
        except KeyError:
            return

app = FlaskApp()
