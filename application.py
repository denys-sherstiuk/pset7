from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import gettempdir

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():
    in_total = 0.0
    
    # take users cash
    rows = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = session["user_id"])
    cash = rows[0]["cash"]
    
    # take users amount of shares   
    rows = db.execute("SELECT symbol, amount FROM UsersStocks WHERE user_id =:id AND amount > 0", id=session["user_id"])
    
    #generated struct of row in index
    for row in rows:
            symbol_data = lookup(row["symbol"])
            row["name"] = symbol_data["name"]
            row["price"] = symbol_data["price"]
            row["total"] = row["price"] * row["amount"]
            in_total += row["total"]
    
    in_total += cash
    
    return render_template("index.html", cash=cash, total=in_total, rows = rows)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure symbol of stock`s and amount was submitted
        if not request.form.get("symbol_stock"):
            return apology("Enter a symbol of stock`s")
        try:
            if not request.form.get("amount") or int(request.form.get("amount")) < 0:
                return apology("Enter amount of stock`s (positive)")
        except ValueError:
            return apology("Enter amount of stock`s (positive integer)")
        
        
        rows = db.execute("SELECT * FROM users WHERE id = :id", id = session["user_id"])
        
        info = lookup(request.form.get("symbol_stock"))
        
        if info:
            # ensure user have enough money
            if rows[0]["cash"] < (info["price"]*int(request.form.get("amount"))):
                return apology("You have not enough money")
        else:
            return apology("No such symbol")
        
        cash=rows[0]["cash"]-info["price"]*int(request.form.get("amount"))
        
        result = db.execute("UPDATE users SET cash =:cash WHERE id =:id", cash=cash, id=session["user_id"])
        result = db.execute("INSERT INTO history (symbol, price, amount, user_id) VALUES( :symbol, :prise, :amount, :user_id)", symbol=info["symbol"], prise=info["price"], amount = int(request.form.get("amount")), user_id=session["user_id"])
        
        return redirect(url_for("history"))
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    
    # take users history 
    history = db.execute("SELECT symbol, amount, date_time, price  FROM history WHERE user_id = :id", id=session["user_id"])
    
    return render_template("history.html", history = history)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
        #return render_template("register.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure symbol of stock`s was submitted
        if not request.form.get("symbol_stock"):
            return apology("Enter a symbol of stock`s")
        
        result = lookup(request.form.get("symbol_stock"))
        message = ""
        
        #generated a message
        if result:
            message = result["name"] +"(" + result["symbol"] + ")" + " cost " + usd(result["price"])
        else:
            return apology("No such symbol")
        return render_template("quoted.html", message=message)
    
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")
        
        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")
        
        # ensure confirm password was submitted
        elif not request.form.get("confirm_password"):
            return apology("must provide confirm password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username not exists
        if len(rows) == 1:
            return apology("username already exist")
        
        # ensure passwords are match
        if request.form.get("password") != request.form.get("confirm_password"):
            return apology("passwords don`t match")
        
        #add to database 
        result = db.execute("INSERT INTO users (username, hash, cash) VALUES( :username, :hash, :cash)", username=request.form.get("username"), hash=pwd_context.encrypt(request.form.get("password")), cash = 10000.0)
        if result != None:
            return render_template("login.html")

        return render_template("register.html")
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure symbol of stock`s and amount was submitted
        if not request.form.get("symbol_stock"):
            return apology("Enter a symbol of stock`s")
        try:
            if not request.form.get("amount") or int(request.form.get("amount")) < 0:
                return apology("Enter amount of stock`s (positive)")
        except ValueError:
            return apology("Enter amount of stock`s (positive integer)")
        
        info = lookup(request.form.get("symbol_stock"))
        rows = ""
        
        if info:
            # take users history of transactions wiht curent symbol
            rows = db.execute("SELECT amount FROM UsersStocks WHERE user_id =:id AND symbol =:symbol", id=session["user_id"], symbol = info["symbol"])
        else:
            return apology("No such symbol")
            
        if rows[0]["amount"] < int(request.form.get("amount")):
            return apology("You have not enought stocks")
        
        rows = db.execute("SELECT cash FROM users WHERE id = :id", id = session["user_id"])
        cash = rows[0]["cash"]+int(request.form.get("amount"))*info["price"]
        result = db.execute("UPDATE users SET cash =:cash WHERE id =:id", cash=cash, id=session["user_id"])
        
        result = db.execute("INSERT INTO history (symbol, price, amount, user_id) VALUES( :symbol, :prise, :amount, :user_id)", symbol=info["symbol"], prise=info["price"], amount = -int(request.form.get("amount")), user_id=session["user_id"])
        
        return redirect(url_for("history"))
    
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("sell.html")

@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    """Change password."""
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        # ensure password was submitted
        if not request.form.get("new_password"):
            return apology("must provide new password")
        
        # ensure confirm password was submitted
        elif not request.form.get("confirm_password"):
            return apology("must provide confirm password")
            
        # ensure passwords are match
        if request.form.get("new_password") != request.form.get("confirm_password"):
            return apology("passwords don`t match") 

        result = db.execute("UPDATE users SET hash =:n_hash WHERE id =:id", n_hash=pwd_context.encrypt(request.form.get("new_password")), id=session["user_id"])
        if result != None:
            return redirect(url_for("history"))

        return render_template("change_password.html")
    
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("change_password.html")