from flask import Flask
import threading

class FlaskApp(threading.Thread):

    app = Flask(__name__)

    def __init__(self):
        threading.Thread.__init__(self)
        self.start()

    def run(self):
        self.app.run()

    @staticmethod
    @app.route('/')
    def index():
        return 'Hello, World!'

app = FlaskApp()
