"""Message View tests."""

# run these tests like:
#
#    FLASK_DEBUG=False python -m unittest test_message_views.py


import os
from re import S
from unittest import TestCase
from app import CURR_USER_KEY

from models import db, Message, User, connect_db

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

# os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app

from app import app, CURR_USER_KEY

app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

connect_db(app)

db.drop_all()
db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class UserBaseViewTestCase(TestCase):
    def setUp(self):

        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)
        db.session.flush()

        db.session.add(u1, u2)
        db.session.commit()

        self.u1_id = u1.id

        self.client = app.test_client()

class UserAddViewTestCase(UserBaseViewTestCase):
    """All of the tests for User views/routes"""

    def test_add_user_success(self):
        """Test functionality for user registration on success"""

        with app.test_client() as client:
            url = "/signup"
            resp = client.post(
                url, data = {
                    "username": "test",
                    "email": "test@email.com",
                    "password": "password",
                    "image_url": None},follow_redirects=True)

            html = resp.get_data(as_text=True)

            #Verify that the correct user page appears after user is created
            self.assertIn("@test", html)

            #Verify that the proper response code is received after user registration
            self.assertEqual(resp.status_code, 200)

    def test_add_user_failure(self):
        """Test functionality for user registration on failure with bad data"""

        with app.test_client() as client:
            url = "/signup"
            resp = client.post(
                url, data = {
                    "username": "baduser",
                    "email": "bademail",
                    "password": "badpassword",
                    "image_url": None},follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertIn("Invalid", html)

            #Verify that the proper response code is received after user registration
            self.assertEqual(resp.status_code, 200)


    def test_login_user_success(self):
        """Test functionality for user login on success"""

        with app.test_client() as client:
            url = "/login"
            resp = client.post(
                url, data = {
                    "username": "u1",
                    "password": "password"
                }, follow_redirects=True
            )

            html = resp.get_data(as_text=True)

            #Verify that the correct user page appears after user is logged in
            self.assertIn("@u1", html)

            #Verify that the proper response code is received after user login
            self.assertEqual(resp.status_code, 200)


    def test_login_user_failure(self):
        """Test functionality for user login on failure with bad data"""

        with app.test_client() as client:
            url = "/login"
            resp = client.post(
                url, data = {
                    "username": "baduser",
                    "password": "badpassword"
                }, follow_redirects=True
            )

            html = resp.get_data(as_text=True)

            #Verify that the correct user page appears after user is logged in
            self.assertIn("Invalid credentials", html)

            #Verify that the proper response code is received after user login
            self.assertEqual(resp.status_code, 200)


    def test_view_profile_logged_in(self):
        """Test if user profiles can be visited if logged in"""

        with app.test_client() as client:

            with client.session_transaction() as session:
                session[CURR_USER_KEY] = self.u1_id

            url = f"/users/{self.u1_id}"
            resp = client.get(url, follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertIn("@u1", html)
            self.assertIn("Messages", html)
            self.assertIn("Following", html)
            self.assertIn("Followers", html)


    def test_view_profile_logged_out(self):
        """Test if user profiles can be visited if logged out"""

        with app.test_client() as client:

            url = f"/users/{self.u1_id}"
            resp = client.get(url, follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertIn("Access unauthorized", html)
