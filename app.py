import os
from dotenv import load_dotenv

from flask import Flask, render_template, request, flash, redirect, session, g, jsonify
from flask_wtf import CSRFProtect
from flask_debugtoolbar import DebugToolbarExtension
from werkzeug.exceptions import Unauthorized
from sqlalchemy.exc import IntegrityError

from forms import (
    CSRFProtectForm, UserAddForm, LoginForm, MessageForm, UserEditForm
)
from models import (
    db, connect_db, User, Message, Like,
    DEFAULT_IMAGE_URL, DEFAULT_HEADER_IMAGE_URL
)

load_dotenv()

CURR_USER_KEY = "curr_user"

csrf = CSRFProtect()
app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ['DATABASE_URL'].replace("postgres://", "postgresql://"))
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
toolbar = DebugToolbarExtension(app)

csrf.init_app(app)

connect_db(app)


##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None

@app.before_request
def add_csrf_form():
    """Add a CSRF form so that every route can use it"""

    g.csrf_form = CSRFProtectForm()

def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Log out user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login and redirect to homepage on success."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(
            form.username.data,
            form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.post('/logout')
def logout():
    """Handle logout of user and redirect to homepage."""

    form = g.csrf_form

    if form.validate_on_submit():
        do_logout()
        flash('You have successfully logged out.')
        return redirect("/login")
    else:
        raise Unauthorized()


##############################################################################
# General user routes:

@app.get('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    if not g.user:
        raise Unauthorized()

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.get('/users/<int:user_id>')
def show_user(user_id):
    """Show user profile."""

    if not g.user:
        raise Unauthorized()

    form = g.csrf_form
    user = User.query.get_or_404(user_id)

    return render_template('users/show.html', user=user, form=form)


@app.get('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        raise Unauthorized()

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.get('/users/<int:user_id>/followers')
def show_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        raise Unauthorized()

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.post('/users/follow/<int:follow_id>')
def start_following(follow_id):
    """Add a follow for the currently-logged-in user.

    Redirect to following page for the current for the current user.
    """

    if not g.user:
        raise Unauthorized()

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.post('/users/stop-following/<int:follow_id>')
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user.

    Redirect to following page for the current for the current user.
    """

    if not g.user:
        raise Unauthorized()

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user
        GET: Shows update profile page for current user.
        POST: Returns updated profile information and adds it to the db
        For non-validation: re-renders the form with error message"""

    if not g.user:
        raise Unauthorized()

    user = g.user
    form = UserEditForm(obj=user)

    if form.validate_on_submit():
        user = User.authenticate(
            form.username.data,
            form.password.data
        )

        if user:
            user.username = form.username.data
            user.email = form.email.data
            user.image_url = form.image_url.data or DEFAULT_IMAGE_URL
            user.header_image_url = (
                form.header_image_url.data or DEFAULT_HEADER_IMAGE_URL
            )
            user.location = form.location.data
            user.bio = form.bio.data

            db.session.commit()

            return redirect(f"/users/{user.id}")
        else:
            flash("Incorrect password", "danger")

    return render_template('users/edit.html', form=form, user=user)


@app.post('/users/delete')
def delete_user():
    """Delete user.

    Redirect to signup page.
    """

    if not g.user:
        raise Unauthorized()

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def add_message():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        raise Unauthorized()

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/create.html', form=form)


@app.get('/messages/<int:message_id>')
def show_message(message_id):
    """Show a message detail."""

    if not g.user:
        raise Unauthorized()

    form = g.csrf_form
    msg = Message.query.get_or_404(message_id)

    return render_template('messages/show.html', msg=msg, form=form)


@app.post('/messages/<int:message_id>/delete')
def delete_message(message_id):
    """Delete a message.

    Check that this message was written by the current user.
    Redirect to user page on success.
    """

    if not g.user:
        raise Unauthorized()

    msg = Message.query.get_or_404(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")

# @app.post('/messages/<int:message_id>/like')
# def toggle_like(message_id):
#     """Toggle like on a message. Redirect to homepage on success."""

#     if not g.user:
#         raise Unauthorized()

#     form = g.csrf_form
#     user = g.user
#     liked_msg = Message.query.get_or_404(message_id)

#     if liked_msg.user_id == g.user.id:
#         flash("You cannot like your own Warble!", "danger")
#         return redirect("/")

#     if form.validate_on_submit():
#         if liked_msg not in user.liked_messages:
#             user.liked_messages.append(liked_msg)
#         else:
#             user.liked_messages.remove(liked_msg)
#     else:
#         raise Unauthorized()

#     db.session.commit()

#     return redirect("/")


@app.get('/users/<int:user_id>/likes')
def show_user_likes(user_id):
    """Display liked messages from user"""

    if not g.user:
        raise Unauthorized()

    form = g.csrf_form
    user = User.query.get_or_404(user_id)

    return render_template("users/likes.html", user=user, form=form)

##############################################################################
# Homepage and error pages


@app.route('/', methods=['GET', 'POST'])
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    form = g.csrf_form

    if g.user:
        following_ids = [f.id for f in g.user.following] + [g.user.id]

        messages = (
            Message
            .query
            .filter(Message.user_id.in_(following_ids))
            .order_by(Message.timestamp.desc())
            .limit(100)
            .all())

        return render_template('home.html', messages=messages, form=form)

    else:
        return render_template('home-anon.html')


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(response):
    """Add non-caching headers on every request."""

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
    response.cache_control.no_store = True
    return response


@app.post("/api/messages/<int:message_id>/like")
def api_toggle_like(message_id):
    """
    Toggle like on a message.
    Return JSON like:
        {favorited: True or False }
    """

    user = g.user
    liked_msg = Message.query.get_or_404(message_id)

    if liked_msg not in user.liked_messages:
        user.liked_messages.append(liked_msg)
        db.session.commit()
        return jsonify(favorited=True) # {favorited: True}
    else:
        user.liked_messages.remove(liked_msg)
        db.session.commit()
        return jsonify(favorited=False)


    ## Get request, convert JSON boolean to python object
    ## read boolean value
    ## process boolean value through if statement -->
    ## update data in database --> create or remove "favorited" relationship
    ## send back confirmation (boolean object converted JSON) in response

    ## if true: return jsonify( {favorited: true} )
