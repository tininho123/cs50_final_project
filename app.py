import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from helpers import error, login_required, clear

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///go.db")

@app.route("/")
@login_required
def index():
    partys = db.execute("SELECT id, date, house_id FROM partys WHERE id IN (SELECT party_id FROM allowed WHERE group_id IN (SELECT username FROM groups WHERE user_id = ?) OR house_id IN (SELECT id FROM houses WHERE admin_id = ?))", session["user_id"], session["user_id"])
    bannes = db.execute("SELECT house_id, final_date FROM banned WHERE user_id = ?", session["user_id"])
    for i in range(len(partys)):
        partys[i]["allowed"] = yes
    for i in range(len(partys)):
        for j in range(len(bannes)):
            if bannes[j]["final_date"] >= partys[i]["date"] and bannes[j]["house_id"] == partys[i]["house_id"]:
                partys[i]["allowed"] = no
        partys[i]["house_id"] = ("SELECT username FROM houses WHERE id = ?", partys[i]["house_id"])
    partys = clear(partys)
    bannes = clear(bannes)
    return render_template("index.html", partys=partys, bannes=bannes, lenp=len(partys), lenb=len(bannes))

@app.route("/group_management", methods=["GET", "POST"])
@login_required
def group_management(sel_gr, members):
    if request.method == "POST":
        if request.form.get("leave_group"):
            db.execute("DROP * FROM groups WHERE user_id = ? AND username = ?", session["user_id"], sel_gr)
            return render_template("leave_group.html", group=sel_gr)
        elif request.form.get("add_member"):
            return add_member(sel_gr)
    else:
        return render_template("group_management.html", username=sel_gr, members=members)

@app.route("/add_member")
@login_required
def add_member(group):
    if request.method == "POST":
        added_member = request.form.get("added_member")
        if db.execute("SELECT id FROM users WHERE username = ?", added_member) == 0:
            return error("not existent user", 407)
        if db.execute("SELECT * FROM groups WHERE user_id = ? AND username = ?", added_member, group):
            return error("member already in the group", 408)
        db.execute("INSERT INTO groups (user_id, username) VALUES (?, ?)", added_member, group)
        return render_template("member_added.html", member=added_member)
    else:
        return render_template("add_member.html", group)

@app.route("/mygroups", methods=["GET", "POST"])
@login_required
def groups():
    if request.method == "POST":
        sel_gr = request.form.get("selected_group")
        members = db.execute("SELECT DISTINCT username FROM users WHERE id = (SELECT user_id FROM groups WHERE username = ?)", sel_gr)
        return group_management(sel_gr, members)
    else:
        groups = db.execute("SELECT username FROM groups WHERE user_id = ?", session["user_id"])
        return render_template("groups.html", groups=groups, len=len(groups))

@app.route("/create_group")
@login_required
def create_group():
    if request.form == "POST":
        group_username = request.form.get("group_username")
        for i in range(4):
            mn = request.form.get("new_member{}".format(i+1))
            if mn:
                db.execute("INSERT INTO groups (user_id, username) VALUES ((SELECT id FROM users WHERE username = ?), ?)", mn, group_username)
        return render_template("group_created.html", group=group_username)
    return render_template("create_group.html")

@app.route("/myhouses")
def houses():
    if request.method == "POST":
        sel_hou = request.form.get("selected_house")
        house_partys = db.execute("SELECT DISTINCT date, id FROM partys WHERE house_id = ?", sel_hou)
        house_bannes = db.execute("SELECT user_id, final_date, id FROM banned WHERE house_id = ?", sel_hou)
        for i in range(len(house_bannes)):
            house_bannes[i]["user_id"] = db.execute("SELECT username FROM users WHERE id = ?", house_bannes[i]["user_id"])
        return house_management(sel_hou, house_partys, house_bannes)
    else:
        houses = db.execute("SELECT username FROM houses WHERE admin_id = ?", session["user_id"])
        return render_template("houses.html", houses=houses, len=len(houses))

@app.route("/house_management")
def house_management(sel_hou, house_partys, house_bannes):
    if request.method == "POST":
        if request.form.get("delete_house"):
            return r_u_sure(sel_hou)
        elif request.form.get("add_ban"):
            return add_ban(sel_hou)
        elif request.form.get("add_party"):
            return add_party(sel_hou)
        elif request.form.get("delete_ban"):
            db.execute("DROP * FROM banned WHERE id = ?", request.form.get("delete_ban"))
            return render_template("ban_deleted.html", user=db.execute("SELECT username FROM users WHERE id = (SELECT user_id FROM banned WHERE id = ?)", request.form.get("dele_ban")), house=sel_hou)
        elif request.form.get("delete_party"):
            db.execute("DROP * FROM partys WHERE id = ?", request.form.get("delete_party"))
            return render_template("party_deleted.html")
    else:
        return render_template("house_management.html", username=sel_hou, partys=house_partys, lenp=len(house_partys), bannes=house_bannes, lenb=len(house_bannes))

@app.route("/r_u_sure")
def r_u_sure(house):
    if request.method == "POST":
        if request.form.get("yes"):
            db.execute("DROP * FROM houses WHERE username = ?", house)
            return render_template("house_deleted.html", house=house)
        else:
            return index()
    else:
        return render_template("r_u_sure.html", house=house)

@app.route("/add_ban")
def add_ban(house):
    if request.method == "POST":
        if not db.execute("SELECT id FROM users WHERE username = ?", request.form.get("user_username")):
            return error("Not existent username", 411)
        db.execute("INSERT INTO banned (house_id, user_id, final_date) VALUES ((SELECT id FROM houses WHERE username = ?), (SELECT id FROM users WHERE username = ?), ?)", house, request.form.get("user_username"), reques.form.get("final_date"))
        return render_template("ban_added.html", username=request.form.get("user_username"), house=house)
    else:
        return render_template("add_ban.html")

@app.route("/add_party")
def add_party(house):
    if request.method == "POST":
        db.execute("INSERT INTO partys (house_id, date) VALUES ((SELECT id FROM houses WHERE username = ?), ?)", house, request.form.get("date"))
        for i in range(4):
            mn = request.form.get("group{}".format(i+1))
            if request.form.get("group{}".format(i+1)):
                if not db.execute("SELECT DISTINCT username FROM groups WHERE username = ?", mn):
                    return error("Not existent group username", 412)
                db.execute("INSERT INTO allowed (group_id, party_id) VALUES (?, (SELECT id FROM partys WHERE house_id = ? AND date = ?))", mn, house, request.form.get("date"))
        return render_template("party_added.html", house=house)
    else:
        return render_template("add_party.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    # Forget any user_id
    session.clear()

    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return error("must provide username", 401)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return error("must provide password", 402)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return error("invalid username or password", 403)

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

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()

    if request.method == "POST":

        if not request.form.get("username"):
            return error("must provide username", 401)

        elif request.form.get("username") in db.execute("SELECT username FROM users"):
            return error("username already exists")

        elif not request.form.get("password"):
            return error("must provide password", 402)

        elif request.form.get("password") != request.form.get("confirmation"):
            return error("confirmation must macth password")

        id = db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", request.form.get("username"), generate_password_hash(request.form.get("password")))

        session["user_id"] = id

        return redirect("/")
    else:
        return render_template("register.html")