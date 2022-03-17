from flask import Flask, render_template, request, session, redirect
import sqlite3
from sqlite3 import Error
from flask_bcrypt import Bcrypt

DATABASE = "C:/Users/18136/OneDrive - Wellington College/13DTS/Smile/smile.db"

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = "marty"


def create_connection(db_file):
    """
    Create a connection with the database
    parameter: name of the database file
    returns: a connection to the file
    """

    try:
        connection = sqlite3.connect(db_file)
        # initialise_tables(connection)
        return connection
    except Error as e:
        print(e)

    return None


def is_logged_in():
    """
    A function to return whether the user is logged in or not
    """
    if session.get("email") is None:
        print("Not logged in")
        return False
    else:
        print("Logged in")
        return True


@app.route('/')
def render_homepage():
    return render_template('home.html', logged_in=is_logged_in())


@app.route('/menu')
def render_menu_page():
    # Connect to the database
    con = create_connection(DATABASE)

    # SELECT the things you want from your task(s)
    query = "SELECT name, description, volume, price, image FROM product"

    cur = con.cursor()  # Creates a cursor tp write the query
    cur.execute(query)  # Runs the query
    product_list = cur.fetchall()  # Puts the results into a list while in python
    print(product_list)
    con.close()

    return render_template('menu.html', products=product_list, logged_in=is_logged_in())


@app.route('/contact')
def render_contact_page():
    return render_template('contact.html', logged_in=is_logged_in())


@app.route('/login', methods=['GET', 'POST'])
def render_login_page():
    if request.method == 'POST':
        print(request.form)
        email = request.form.get('email').lower().strip()
        password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(password)
        print(hashed_password)
        con = create_connection(DATABASE)
        query = "SELECT id, fname, password FROM user WHERE email=?"
        cur = con.cursor()
        cur.execute(query, (email,))
        user_data = cur.fetchall()
        con.close()

        if user_data:
            user_id = user_data[0][0]
            first_name = user_data[0][1]
            db_password = user_data[0][2]
        else:
            return redirect("/login?error=Email+or+password+is+incorrect")

        if not bcrypt.check_password_hash(db_password, password):
            return redirect("/login?error=Email+or+password+is+incorrect")

        session['email'] = email
        session['user_id'] = user_id
        session['fname'] = first_name
        session['cart'] = []
        return redirect('/menu')

    return render_template('login.html', logged_in=is_logged_in())


@app.route('/logout')
def render_logout_page():
    print(list(session.keys()))
    [session.pop(key) for key in list(session.keys())]
    print(list(session.keys()))
    return redirect('/?message=See+you+next+time')


@app.route('/signup', methods=['GET', 'POST'])
def render_signup_page():
    if request.method == 'POST':
        print(request.form)
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        password = request.form.get('password')
        password2 = request.form.get('password2')

        if password != password2:
            return redirect('/signup?error=Passwords+do+not+match')
        print(password, len(password))
        if len(password) < 8:
            print(password, len(password), len(password) < 8)
            return redirect('/signup?error=Passwords+must+be+at+least+8+characters')

        hashed_password = bcrypt.generate_password_hash(password)

        con = create_connection(DATABASE)

        query = "INSERT INTO user(id, fname, lname, email, password) VALUES(NULL,?,?,?,?)"

        cur = con.cursor()

        cur.execute(query, (fname, lname, email, hashed_password))  # executes the query
        con.commit()
        con.close()
        return redirect('/login')

    error = request.args.get('error')
    if error == None:
        error = ""
    return render_template('signup.html', error=error, logged_in=is_logged_in())


app.run(host='0.0.0.0', debug=True)
