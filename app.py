import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    rows = db.execute(
        "SELECT symbol, shares FROM portfolio WHERE user_id=?;", session["user_id"]
    )

    cash = db.execute("SELECT cash FROM users WHERE id=?;", session["user_id"])[0]["cash"]
    net_value = 0
    invested_value = 0
    current_price = {}
    for row in rows:
        current_price[row["symbol"]] = lookup(row["symbol"])["price"]
        invested_value += row["shares"] * current_price[row["symbol"]]
        row["current_price"] = current_price[row["symbol"]]

    net_value = invested_value + cash

    return render_template("index.html", rows=rows, invested_value=invested_value, net_value=net_value, cash=cash, current_price=current_price)


# Other route handlers remain unchanged


if __name__ == "__main__":
    # Run the app, specifying host and port for compatibility with Vercel
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
