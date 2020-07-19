from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask import request, redirect, Response
from logging.handlers import RotatingFileHandler
from src.salt import hash_password, verify_password
from src.config import config
from pathlib import Path
import threading
import json
import time
import logging
import sys
import traceback
import datetime
import src.database

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
Path("log/").mkdir(exist_ok=True)

fileHandler = RotatingFileHandler('log/latest.log', mode='a', maxBytes=5242880, backupCount=2)
fileHandler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s:%(name)s:%(message)s'))
logger.addHandler(fileHandler)

def uncaughtExceptionHandler(etype, value, tb):
    formatted_exception = ' '.join(traceback.format_exception(etype, value, tb))
    print(formatted_exception)
    logger.error(f"Uncaught exception: {formatted_exception}")

sys.excepthook = uncaughtExceptionHandler


def monthlyClearSessions():
    """
    Clear old sessions monthly.
    """
    global sessions
    while True:
        sessions = getStoredSessions()
        for _ in range(200):
            time.sleep(1315)

def getStoredSessions():
    """
    Pull stored sessions from database, delete sessions older than a month.
    return: sessions dictionary
    """
    sessions = {}
    sessionsToDelete = []
    for s in db.getSessions():
        s_year, s_month, s_day = [int(x) for x in s[3].split('-')]
        s_date = datetime.date(s_year, s_month, s_day)
        if s_date + datetime.timedelta(days=30) < datetime.date.today():
            sessionsToDelete.append((s[0], ))
            continue
        sessions[s[0]] = {'username': s[1], 'usertype': s[2], 'date': s_date}
    if sessionsToDelete:
        db.deleteSessions(sessionsToDelete)
    return sessions

db = src.database.Database()
sessionSecret = json.load(open('keys.json'))['sessionSecret']
sessions = {}

monthlyClearSessionsThread = threading.Thread(target=monthlyClearSessions)
monthlyClearSessionsThread.start()

class FlaskApp(threading.Thread):

    app = Flask(__name__)
    socketio = SocketIO(app)

    def __init__(self):
        threading.Thread.__init__(self)
        self.start()

    def run(self):
        self.socketio.run(self.app, host='0.0.0.0', port=config['flaskPort'], log_output=config['flaskLogging'])

    @staticmethod
    @app.route('/')
    def index():
        """
        Index page checks for a session cookie,
        redirect to userprofile (if cookie found) or login page.
        """
        SID = request.cookies.get("SID")
        session = sessions.get(SID)
        if session:
            return redirect(f'/u/{session["username"]}', code=302)
        return redirect('/login', code=302)

    @staticmethod
    @app.route('/login')
    def login():
        """
        Login page does signup and login (username+password)
        """
        return render_template('login.html', host=config['flaskHost'], port=config['flaskPort'], version=round(time.time()))

    @staticmethod
    @app.route('/u/<username>')
    def linkprofile(username):
        """
        User page checks if user exists,
        updates session and loads profile if session is valid.
        """
        username = username.lower()
        userinfo = db.getUser(username)
        if not userinfo:
            return Response("User not found", status=404)
        SID = request.cookies.get("SID")
        session = sessions.get(SID)
        if session and (session['username'] == username or session['usertype'] == 'admin'):
            newdate = datetime.date.today()
            session['date'] = newdate
            db.updateSessionDate(SID, f'{newdate.year}-{newdate.month}-{newdate.day}')
            return render_template('userprofile.html', username=username, displayname=userinfo[0], 
                                    host=config['flaskHost'], port=config['flaskPort'], version=round(time.time()))
        return Response("401 Unauthorized", status=401)

    @staticmethod
    @socketio.on('login')
    def onlogin(message):
        """
        Login event comes from JavaScript side.
        If user exists: verify password, create new session,
        send error message if wrong password.
        Or register user: hash password, create new session, add user to database.
        Emit create cookie and redirect to profile.
        """
        username = message['username']
        password = message['password']
        userinfo = db.getUser(username)
        if userinfo:
            hashed_pwd = userinfo[1]
            usertype = userinfo[2]
            if verify_password(hashed_pwd, password):
                SID = hash_password(sessionSecret)
                date = datetime.date.today()
                sessions[SID] = {'username': username, 'usertype': usertype, 'date': date}
                db.addSession(SID, username, usertype, f'{date.year}-{date.month}-{date.day}')
                emit('loginSuccess', {'username': username, 'SID': SID})
                logger.info(f'login user {username}')
            else:
                emit('loginFail')
                logger.info(f'failed login user {username}')
            return
        hashed_pwd = hash_password(password)
        SID = hash_password(sessionSecret)
        date = datetime.date.today()
        sessions[SID] = {'username': username, 'usertype': 'user', 'date': date}
        db.addUser(username, message["displayname"], hashed_pwd, 'user')
        db.addSession(SID, username, 'user', f'{date.year}-{date.month}-{date.day}')
        emit('loginSuccess', {'username': username, 'SID': SID})
        logger.info(f'register user {username}')

    @staticmethod
    @socketio.on('logout')
    def onlogout(message):
        """
        Logout event comes from JavaScript side.
        Delete session from memory and database, emit delete cookie, redirect to index page.
        Emit page reload if session not found.
        """
        try:
            del sessions[message['SID']]
            db.deleteSession(message['SID'])
            emit('logout')
        except KeyError:
            emit('unknownSession')

    @staticmethod
    @socketio.on('clearSID_onlogin')
    def clearSID_onlogin(message):
        """
        Delete old session cookie on successful login,
        redirect to profile if session not found.
        """
        try:
            del sessions[message['SID']]
            db.deleteSession(message['SID'])
        except KeyError:
            emit('userprofileRedirect')

app = FlaskApp()
