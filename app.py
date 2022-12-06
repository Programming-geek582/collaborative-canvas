from flask import Flask, render_template, make_response, redirect, url_for, request, session, g, jsonify
from flask_nav import Nav
from flask_nav.elements import Navbar, View, Subgroup, Separator, Link
from flask_bootstrap import Bootstrap
from peewee import SqliteDatabase, IntegrityError
from database import User, Pixels
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import bcrypt  # for hashing
import re # for regex


app = Flask(__name__)
Bootstrap(app)
nav = Nav()

app.secret_key = 'SuperSecretKeyForAgileProject'
db = SqliteDatabase('pixr.sqlite')
# init for managing logins
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@nav.navigation()
def mynavbar():
    """ Navigation bar with flask-bootstrap """
    if current_user.is_authenticated:
        return Navbar(
            'Menu',
            View('Home', 'home'),
            View('Profile', 'profile'),
            View(f'Logout {g.user.username}', 'logout')
        )
    else:
        return Navbar(
            'Menu',
            View('Home', 'home'),
            View('Login', 'login'),
            View('Register', 'register')
        )


@app.before_request
def get_db():
    """ Initialize connection with database"""
    db.connect()


@app.before_request
def before_request():
    """ For sessions """
    g.user = {}
    if 'user_id' in session:
        user = User.get(User.id == session['user_id'])
        g.user = user
    else:
        g.user['username'] = ''


@app.teardown_request
def close_connection(exception):
    """ For closing database when not in use """
    if not db.is_closed():
        db.close()


@app.route('/home', methods=['GET'])
def home():
    """ Route to project homepage """
    return make_response(render_template('index.html'), 200)


@app.route('/', methods=['GET'])
def default():
    """ secondary route to homepage """
    return make_response(render_template('index.html'), 200)


@login_manager.user_loader
def load_user(user_id):
    """ Required for managing user login """
    return User.get(user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """ Logs User in """
    error = ''
    if request.method == 'POST':
        session.pop('user_id', None) # reset session
        username = request.form["username"]
        passwd = request.form["password"]
        try:
            loginUser = User.get(User.username == username)
        except:
            return make_response(render_template('login.html', error='A user with that username does not exist.'), 400)
        try:
            if loginUser and bcrypt.checkpw(passwd.encode("utf-8"), loginUser.password.encode("utf-8")):
                # If hashed passwords match, then generate session and login user
                print(loginUser.password)
                session["user_id"] = User.get(User.username == username).id
                login_user(loginUser)
                return make_response(redirect(url_for('profile',username=username)), 302)
        except ValueError:
            error = "Invalid password."
            return make_response(render_template('login.html', error=error), 400)
    else:
        return make_response(render_template('login.html', error=''), 200)

@app.route('/profile')
def profile():
    """ Displays User Profile """
    return render_template("profile.html", username=g.user.username.title())

@app.route('/profile/<username>')
def userprofile(username):
    """ Displays canvas for <username> """
    return render_template("profile.html", username=username.title())

@app.route('/register', methods=['GET', 'POST'])
def register():
    """ Registers a new user and hashes password, also logs in after """
    error = ''
    if request.method == 'POST':
        username = request.form["new_username"]
        password = request.form["new_password"]
        v_password = request.form["v_password"]

        # Verify password is typed correctly
        if v_password != password:
            return render_template('register.html', error='Passwords do not match')

        reg = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{6,20}$"

        # compiling regex
        pat = re.compile(reg)
        # searching regex
        mat = re.search(pat, password)
        # validating conditions
        if mat:
            password = request.form["new_password"].encode("utf-8")
            print("Password is valid.")
        else:

            return make_response(render_template('register.html', error="Password is invalid: \n"
                                                          "Must be 6-8 characters, \n"
                                                          "contain one number, one uppercase letter, and "
                                                          "one symbol"), 400)

        if User.select().where(User.username == username).exists():
            return make_response(render_template('register.html', error='A user with that username already exists.'), 400)
        hashed = bcrypt.hashpw(password, bcrypt.gensalt())
        newuser = User.create(username=username, password=hashed)
        session["user_id"] = User.get(User.username == newuser.username).id
        login_user(newuser)
        return make_response(redirect(url_for('profile',username=username)), 302)
    if request.method == 'GET':
        return make_response(render_template('register.html', error=error), 200)


@app.route('/logout')
@login_required
def logout():
    """ Logs user out when called """
    logout_user()
    session.pop('user_id', None)  # reset session
    return make_response(redirect(url_for('login')), 302)


# ---------------------------------------- Main Canvas API ---------------------------------------------
@app.route('/canvas/<user>', methods=['POST'])
def store_pixels(user):
    """ Route for storing pixels to database """
    # Stores the pixel ids and their colors
    # JSON data structure = { pixel1 : color, pixel2 : color ...... }
    data = request.json
    old_pixels = Pixels.delete().where(Pixels.user == user)
    old_pixels.execute()

    for pixel in data:
        try:
            pixel = Pixels.insert(user=user, pixel=pixel, color=data[pixel]).execute()
        except IntegrityError as e:
            return make_response(str(e), 400)
    return make_response("Saved", 200)


@app.route('/canvas/<user>', methods=['GET'])
def get_pixels(user):
    """ Route for getting pixels for a particular user's database"""
    dict = {}
    data = Pixels.select().where(Pixels.user_id == user).execute()
    for i in data:
        dict[i.pixel] = i.color

    return make_response(jsonify(dict))


if __name__ == '__main__':
    nav.init_app(app)
    app.run(debug=True)
