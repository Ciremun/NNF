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

def clearSessions():
    global sessions
    sessions.clear()

class FlaskApp(threading.Thread):

    app = Flask(__name__)
    socketio = SocketIO(app)

    def __init__(self):
        threading.Thread.__init__(self)
        self.start()

        db.createUsersTable()

    def run(self):
        self.socketio.run(self.app, host='0.0.0.0', port=config['flaskPort'], log_output=config['flaskLogging'])

    @staticmethod
    @app.route('/')
    def index():
        return redirect('/login', code=302)

    @staticmethod
    @app.route('/login')
    def login():
        return render_template('login.html', host=config['flaskHost'], port=config['flaskPort'], version=round(time.time()))

    @staticmethod
    @app.route('/u/<username>')
    def linkprofile(username):
        username = username.lower()
        userinfo = db.getUser(username)
        if not userinfo:
            return Response("User not found", status=404)
        SID = request.cookies.get("SID")
        session = sessions.get(SID)
        if session and (session['username'] == username or session['usertype'] == 'admin'):
            return render_template('userprofile.html', username=username, displayname=userinfo[0], 
                                    host=config['flaskHost'], port=config['flaskPort'], version=round(time.time()))
        return Response("401 Unauthorized", status=401)

    @staticmethod
    @socketio.on('login')
    def onlogin(message):
        username = message['username']
        password = message['password']
        userinfo = db.getUser(username)
        if userinfo:
            hashed_pwd = userinfo[1]
            usertype = userinfo[2]
            if verify_password(hashed_pwd, password):
                SID = hash_password(sessionSecret)
                sessions[SID] = {'username': username, 'usertype': usertype}
                emit('loginSuccess', {'username': username, 'SID': SID})
                print(f'login user {username}')
            else:
                emit('loginFail')
                print(f'failed login user {username}')
            return
        hashed_pwd = hash_password(password)
        db.addUser(username, message["displayname"], hashed_pwd, 'user')
        SID = hash_password(sessionSecret)
        sessions[SID] = {'username': username, 'usertype': 'user'}
        emit('loginSuccess', {'username': username, 'SID': SID})
        print(f'register user {username}')

    @staticmethod
    @socketio.on('logout')
    def onlogout(message):
        try:
            del sessions[message['SID']]
            emit('logout')
        except KeyError:
            emit('unknownSession')

    @staticmethod
    @socketio.on('clearSID')
    def onclearSID(message):
        try:
            del sessions[message['SID']]
        except KeyError:
            emit('unknownSession')

app = FlaskApp()
