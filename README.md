# nam-nyam-foods
nam-nyam parser, office food management  

## Install

### req

    requests==2.24.0
    beautifulsoup4==4.9.1
    lxml==4.5.2
    pandas==1.0.5
    XlsxWriter==1.2.9
    Flask==1.1.2
    gevent==20.6.2
    psycopg2==2.8.5

Tested on Python 3.7.8  

### config.json

`flaskLogging` (boolean): server logs to console  

### keys.json

`sessionSecret` (str): random string for session ID hashing  
`PostgreDatabase` (str): database name  
`PostgreUser` (str)  
`PostgrePassword` (str)  
`PostgreHost` (str)  
`PostgrePort` (int/str)  
`flaskPort` (int/str)  
