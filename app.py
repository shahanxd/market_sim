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
        "SELECT symbol , shares FROM PORTFOLIO WHERE user_id=? ;", session["user_id"])

    cash = db.execute("SELECT cash FROM users WHERE id=? ;",
                      session["user_id"])[0]['cash']
    net_value = 0
    invested_value = 0
    current_price = {}
    for row in rows:
        current_price[row['symbol']] = lookup(row['symbol'])["price"]
        invested_value += row['shares']*current_price[row['symbol']]
        row["current_price"] = current_price[row['symbol']]

    net_value = invested_value + cash

    return render_template("index.html", rows=rows, invested_value=invested_value, net_value=net_value, cash=cash, current_price=current_price)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    symbol = request.form.get("symbol")
    quote_data = lookup(symbol)
    if not symbol:
        return apology("ENTER A DAMN SYMBOL!")
    if not quote_data:
        return apology("WHA-? BRO THIS SYMBOL ONLY EXISTS ON NEPTUNE STOCK EXCHANGE")

    shares = request.form.get("shares")
    if not shares:
        return apology("NUMBER. N_U_M_B_E_R. ENTER NUMBER OF SHARES!")
    try:
        shares = int(shares)
    except ValueError:
        return apology("NATURAL NUMBER. PLEASE. OR ELSE..")

    if shares <= 0:
        return apology("I NEED SOME OF WHATEVER YOU ON, CUZ YOU CAN ONLY BUY POSITIVE NUMBER OF SHARES")

    cash = db.execute("SELECT cash FROM users WHERE id=?",
                      session["user_id"])[0]["cash"]

    amt_needed = quote_data["price"] * shares

    if cash < amt_needed:
        return apology("ERROR: YOU POOR")
    db.execute("UPDATE users SET cash=? WHERE id=? ;",
               cash-amt_needed, session["user_id"])

    if not db.execute("SELECT * FROM portfolio WHERE symbol=? ;", quote_data["symbol"]):
        db.execute("INSERT INTO portfolio (user_id , symbol , shares, buy_price) VALUES (? , ? , ?, ?) ;",
                   session["user_id"], quote_data["symbol"], shares, quote_data["price"])
    else:
        total_shares = (db.execute("SELECT shares FROM portfolio WHERE user_id=? AND symbol=?;",
                        session["user_id"], quote_data["symbol"])[0]['shares'])+shares
        db.execute("UPDATE portfolio SET shares=? WHERE symbol=? ;",
                   total_shares, quote_data["symbol"])

    db.execute("INSERT INTO transactions (user_id , symbol , shares , price, type) VALUES (? , ? , ? , ? , ?)",
               session["user_id"], quote_data["symbol"], shares, quote_data["price"], "BUY")
    return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    rows = db.execute(
        "SELECT symbol , shares , price , type FROM TRANSACTIONS WHERE user_id=? ;", session["user_id"])

    return render_template("history.html", rows=rows)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get(
                "username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "GET":
        return render_template("quote.html")

    else:
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("ENTER A DAMN SYMBOL!")
        quote_info = lookup(symbol)
        if quote_info == None:
            return apology("WHA-? BRO THIS SYMBOL ONLY EXISTS ON NEPTUNE STOCK EXCHANGE")
        return render_template("quoted.html", name=quote_info["name"], price=quote_info["price"], symbol=quote_info["symbol"])


@app.route("/change_pass", methods=["GET", "POST"])
def change_pass():

    if request.method == "GET":
        return render_template("change_pass.html")
    else:
        new_pass = request.form.get("new_pass")
        conf_new_pass = request.form.get("conf_new_pass")

        if not new_pass:
            return apology("PASSWORD IS JOHN CENA")
        if not conf_new_pass:
            return apology("PASSWORD CONFIRMATION IS JOHN CENA")
        if new_pass != conf_new_pass:
            return apology("PASSWORDS DON'T MATCH. LMAO.")
        db.execute("UPDATE users SET hash=? WHERE id=? ;", generate_password_hash(
            new_pass, method='scrypt', salt_length=16), session["user_id"])
        return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("USERNAME IS JOHN CENA")
        if not password:
            return apology("PASSWORD IS JOHN CENA")
        if not confirmation:
            return apology("PASSWORD CONFIRMATION IS JOHN CENA")

        username_taken = db.execute(
            "SELECT username FROM users WHERE username=? ;", username)
        if username_taken:
            return apology("USERNAME TAKEN. BUY FOR $20M. JK.")

        if password != confirmation:
            return apology("PASSWORDS DON'T MATCH. LMAO.")

        db.execute("INSERT INTO users (username , hash) VALUES (? , ?)", username,
                   generate_password_hash(password, method='scrypt', salt_length=16))
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "GET":
        rows = db.execute(
            "SELECT symbol FROM portfolio WHERE user_id=? ;", session["user_id"])
        return render_template("sell.html", rows=rows)
    else:
        shares = int(request.form.get("shares"))
        symbol = request.form.get("symbol")

        if not shares:
            return apology("DUH. HOW MANY?")
        if shares == 0:
            return apology("WHY. WHY EVEN TRY. 0. REALLY.")
        if shares < 0:
            return apology("SELL -VE SHARES? THAT'S BUYING, YOU -")
        if not symbol:
            return apology("SELECT AN ASSET. IT'S A DROP DOWN. NEVER SEEN ONE?")

        quote_data = lookup(symbol)
        total_shares = db.execute(
            "SELECT shares FROM portfolio WHERE user_id=? AND symbol=? ;", session["user_id"], symbol)
        total_shares = int(total_shares[0]['shares'])

        if shares < total_shares:
            db.execute("UPDATE portfolio SET shares=shares-? WHERE user_id=? AND symbol=? ;",
                       shares, session["user_id"], symbol)
            db.execute("INSERT INTO transactions (user_id , symbol , shares , price , type) VALUES (? , ? , ?, ? , ?)",
                       session["user_id"], quote_data["symbol"], shares, quote_data["price"], "SELL")

        elif shares == total_shares:
            db.execute("DELETE FROM portfolio WHERE user_id=? AND symbol=? ;",
                       session["user_id"], symbol)
            db.execute("INSERT INTO transactions (user_id , symbol , shares , price , type) VALUES (? , ? , ?, ? , ?)",
                       session["user_id"], quote_data["symbol"], shares, quote_data["price"], "SELL")

        elif shares > total_shares:
            return apology("BRO TRYNA SELL WHAT YOU AIN'T OWN?!")

        db.execute("UPDATE users SET cash=cash+? WHERE id=? ;",
                   quote_data["price"]*shares, session["user_id"])

        return redirect("/")
