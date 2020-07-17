from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask import request, redirect, Response
import threading
import json
import src.database
from src.salt import hash_password, verify_password

db = src.database.Database()
sessions = {}

class FlaskApp(threading.Thread):

    app = Flask(__name__)
    socketio = SocketIO(app)

    def __init__(self):
        threading.Thread.__init__(self)
        self.start()

        db.createUsersTable()

    def run(self):
        self.socketio.run(self.app, host='localhost', port=5001)

    @staticmethod
    @app.route('/')
    def index():
        username = sessions.get(request.remote_addr)
        if username:
            return redirect(f'/u/{username}', code=302)
        return render_template('login.html', ip=request.remote_addr)

    @staticmethod
    @app.route('/u/<username>')
    def userprofile(username):
        username = username.lower()
        displayname = db.getUserDisplayname(username)
        if not displayname:
            return Response("User not found", status=404)
        elif not sessions.get(request.remote_addr) == username.lower():
            return Response("401 Unauthorized", status=401)
        return render_template('userprofile.html', username=username,
                                displayname=displayname[0][0], ip=request.remote_addr)

    @staticmethod
    @socketio.on('login')
    def login(message):
        user = message['username']
        password = message['password']
        hashed_pwd = db.getUserPasswordHash(user)
        if hashed_pwd:
            hashed_pwd = hashed_pwd[0][0]
            print(f'login status {verify_password(hashed_pwd, password)}')
            if verify_password(hashed_pwd, password):
                sessions[message['ip']] = user
                emit('loginSuccess', {'username': user})
                print(f'login user {user}')
            else:
                emit('loginFail')
                print(f'failed login user {user}')
            return
        hashed_pwd = hash_password(password)
        db.addUser(user, message["displayname"], hashed_pwd)
        sessions[message['ip']] = user
        emit('loginSuccess', {'username': user})
        print(f'register user {user}')

    @staticmethod
    @socketio.on('logout')
    def logout(message):
        del sessions[message['ip']]
        emit('mainPageRedirect')

app = FlaskApp()
