"""Flask app — public-facing portfolio site with maps and charts."""

from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/map")
def map_view():
    return render_template("map.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
