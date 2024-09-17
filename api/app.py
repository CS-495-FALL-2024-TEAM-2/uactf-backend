from flask import Flask

app = Flask(__name__)

@app.route("/")
def get_main_route():
    return {"content" : "Welcome to the UA CTF Backend!"}, 200
