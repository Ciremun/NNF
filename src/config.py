from os.path import join, dirname

from dotenv import load_dotenv

flaskLogging = True
https = False

users_can_order = True

load_dotenv(join(dirname(__name__), '.env'))
