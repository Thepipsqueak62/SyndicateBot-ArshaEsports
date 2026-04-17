from flask import Flask
from threading import Thread

from shared_code.data_handlers.read_config import get_web_host

app = Flask('')

host_ip = get_web_host()
@app.route('/')
def home():
    return "_ArcheRage Events Bot 🟢"


def run():
    app.run(host=host_ip, port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()
