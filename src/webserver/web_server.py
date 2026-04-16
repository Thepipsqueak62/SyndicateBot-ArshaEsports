from flask import Flask
from threading import Thread
from configparser import ConfigParser

config = ConfigParser()
config.read('config.ini')

# Config.ini WebServerSettings
host = config["WebServerSettings"]['host']

app = Flask('')


@app.route('/')
def home():
    return "_ArcheRage Events Bot 🟢"


def run():
    app.run(host=host, port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()
