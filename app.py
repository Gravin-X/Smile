from flask import Flask, render_template, request, session, redirect
import sqlite3
from sqlite3 import Error
from flask_bcrypt import Bcrypt
from datetime import datetime
import smtplib, ssl
from smtplib import SMTPAuthenticationError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

DATABASE = "C:/Users/18136/OneDrive - Wellington College/13DTS/Smile/smile.db"
# DATABASE = "C:/Users/ramig/OneDrive - Wellington College/13DTS/Smile/smile.db"

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
        connection.execute('pragma foreign_keys=ON')
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
    query = "SELECT id, name, description, volume, image, price FROM product"

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


@app.route('/addtocart/<productid>')
def addtocart(productid):
    if not is_logged_in():
        redirect('/')

    try:
        productid = int(productid)
    except ValueError:
        print("{} is not an integer".format(productid))
        return redirect(request.referrer + "?error=Invalid+product+id")

    userid = session['user_id']
    timestamp = datetime.now()
    print("User {} would like to add {} to cart".format(userid, productid, timestamp))

    query = "INSERT INTO cart(id,userid,productid,timestamp) VALUES (NULL,?,?,?)"
    con = create_connection(DATABASE)
    cur = con.cursor()
    # try to INSERT - this will fail if there is a foreign key issue
    try:
        cur.execute(query, (userid, productid, timestamp))
    except sqlite3.IntergrityError as e:
        print(e)
        print("### PROBLEM INSERTING INTO DATABASE - FOREIGN KEY ###")
        con.close()
        return redirect('/menu?error=Something+went+very+very+wrong')
    # everything works, commit the insertion or the system will immediately roll it back
    cur.execute(query, (userid, productid, timestamp))
    con.commit()
    con.close()

    return redirect('/menu')


@app.route('/cart')
def render_cart():
    userid = session['user_id']
    query = "SELECT productid FROM cart WHERE userid=?;"
    con = create_connection(DATABASE)
    cur = con.cursor()
    cur.execute(query, (userid,))
    product_ids = cur.fetchall()
    print(product_ids)  # U - G - L - Y

    if len(product_ids)==0:
        return redirect('/menu?error=Cart+empty')

    # the results from the query are a list of sets, loop through and pull out the ids
    for i in range(len(product_ids)):
        product_ids[i] = product_ids[i][0]
    print(product_ids)

    unique_product_ids = list(set(product_ids))

    for i in range(len(unique_product_ids)):
        product_count = product_ids.count(unique_product_ids[i])
        unique_product_ids[i] = [unique_product_ids[i], product_count]
    print(unique_product_ids)

    query = """SELECT name, price FROM product WHERE id =?;"""
    for item in unique_product_ids:
        cur.execute(query, (item[0],))
        item_details = cur.fetchall()
        print(item_details)
        item.append(item_details[0][0])
        item.append(item_details[0][1])

    con.close()
    print(unique_product_ids)

    return render_template('cart.html', cart_data=unique_product_ids, logged_in=is_logged_in())


@app.route('/removefromcart/<productid>')
def remove_from_cart(productid):
    print("Remove {}".format(productid))
    customer_id = session['user_id']
    query = "DELETE FROM cart WHERE id=(SELECT MIN(id) FROM cart WHERE productid=? and userid=?);"
    con = create_connection(DATABASE)
    cur = con.cursor()
    cur.execute(query, (productid, customer_id))
    con.commit()
    con.close()
    return redirect('/cart')


@app.route('/confirmorder')
def confirmorder():
    userid = session['user_id']
    query = "SELECT productid FROM cart WHERE userid=?;"
    con = create_connection(DATABASE)
    cur = con.cursor()
    cur.execute(query, (userid,))
    product_ids = cur.fetchall()
    print(product_ids)  # U - G - L - Y

    if len(product_ids) == 0:
        return redirect('/menu?error=Cart+empty')

    # convert the result to a nice list
    for i in range(len(product_ids)):
        product_ids[i] = product_ids[i][0]

    unique_product_ids = list(set(product_ids))

    for i in range(len(unique_product_ids)):
        product_count = product_ids.count(unique_product_ids[i])
        unique_product_ids[i] = [unique_product_ids[i], product_count]

    query = """SELECT name, price FROM product WHERE id = ?;"""
    for item in unique_product_ids:
        cur.execute(query, (item[0],))  # item[0] is the productid
        item_details = cur.fetchall()  # create a list
        item.append(item_details[0][0])  # add the product name to the list
        item.append(item_details[0][1])  # add the price to the list

    query = "DELETE FROM cart WHERE userid=?;"
    cur.execute(query, (userid,))
    con.commit()
    con.close()
    send_confirmation(unique_product_ids)
    return redirect('/?message=Order+complete')


def send_confirmation(order_info):
    print(order_info)
    email = session['email']
    firstname = session['fname']
    SSL_PORT = 465  # For SSL

    sender_email = input("Gmail address: ").strip()
    sender_password = input("Gmail password: ").strip()
    table = "<table>\n<tr><th>Name</th><th>Quantity</th><th>Price</th><th>Order total</th></tr>\n"
    total = 0
    for product in order_info:
        name = product[2]
        quantity = product[1]
        price = product[3]
        subtotal = product[3] * product[1]
        total += subtotal
        table += "<tr><td>{}</td><td>{}</td><td>{:.2f}</td><td>{:.2f}</td></tr>\n".format(name, quantity, price,
                                                                                          subtotal)
    table += "<tr><td></td><td></td><td>Total:</td><td>{:.2f}</td></tr>\n</table>".format(total)
    print(table)
    print(total)
    html_text = """<p>Hello {}.</p>
   <p>Thank you for shopping at smile cafe. Your order summary:</p>"
   {}
   <p>Thank you, <br>The staff at smile cafe.</p>""".format(firstname, table)
    print(html_text)

    context = ssl.create_default_context()
    message = MIMEMultipart("alternative")
    message["Subject"] = "Your order with smile"

    message["From"] = "smile cafe"
    message["To"] = email

    html_content = MIMEText(html_text, "html")
    message.attach(html_content)
    with smtplib.SMTP_SSL("smtp.gmail.com", SSL_PORT, context=context) as server:
        try:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, message.as_string())
        except SMTPAuthenticationError as e:
            print(e)


app.run(host='0.0.0.0', debug=True)
