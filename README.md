# nam-nyam-foods

nam-nyam.ru parser, office food management  

## Install

[Python](https://python.org/)  

### env

|      Key       |  Type |            Value            |
|----------------|-------|-----------------------------|
| `SECRET_KEY`   | `str` | session ID hashing password |
| `DATABASE_URL` | `str` | postgres [connection URI](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING) `postgres://{user}:{password}@{hostname}:{port}/{database-name}` |
| `FLASK_PORT`   | `int` | flask app port |
| `FLASK_HOST`   | `str` | flask app host |

### src/config.py

|      Key        |  Type  |            Value            |
|-----------------|--------|-----------------------------|
| flaskLogging    | `bool` | server logs?                |
| https           | `bool` |                             |
