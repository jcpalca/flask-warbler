"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase
from sqlalchemy import exc

from models import db, User, Message, Follows, connect_db

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

# os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

connect_db(app)

db.drop_all()
db.create_all()


class UserModelTestCase(TestCase):
    """Tests for User Model"""
    def setUp(self):
        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)

        db.session.commit()
        self.u1_id = u1.id
        self.u2_id = u2.id

        self.client = app.test_client()

    def tearDown(self):
        db.session.rollback()

    def test_user_model(self):
        u1 = User.query.get(self.u1_id)

        # User should have no messages & no followers
        self.assertEqual(len(u1.messages), 0)
        self.assertEqual(len(u1.followers), 0)

    def test_repr(self):
        """ Test that the repr displays what it is supposed to."""
        u1 = User.query.get(self.u1_id)

        self.assertEqual(u1.__repr__(), "<User #1: u1, u1@email.com>")

    def test_user_following(self):
        """ Test is user following functionality works properly"""
        u1 = User.query.get(self.u1_id)
        u2 = User.query.get(self.u2_id)

        u1.following.append(u2)
        db.session.commit()

        # Test if user1 is successfully following user2
        self.assertTrue(u1.is_following(u2))

        # Test if user2 is NOT following user 1
        self.assertFalse(u2.is_following(u1))

        # Test is user2 is successfully being followed by user1
        self.assertTrue(u2.is_followed_by(u1))

        # Test if user1 is NOT being followed by user2
        self.assertFalse(u1.is_followed_by(u2))


    def test_user_signup(self):
        """Test user signup functionality"""
        u1 = User.query.get(self.u1_id)

        test_user = {
            "username": 'u1',
            "email": "u1@email.com",
            "password": 'password',
            "image_url": "/static/images/default-pic.png"
        }

        #Test is user1 data in database is the same as the data
        #that was passed in
        self.assertEqual(u1.username, test_user['username'])
        self.assertEqual(u1.email, test_user['email'])
        self.assertNotEqual(u1.password, test_user['password'])
        self.assertEqual(u1.image_url, test_user['image_url'])


    def test_user_failed_signup_not_unique(self):
        """Test the validation on the user sign up form when input is not unique"""

        with self.assertRaises(exc.IntegrityError):
            User.signup("u1", "u1@email2.com", "password", None)
            db.session.flush()


    def test_user_failed_signup_null(self):
        """Test the validation on the user sign up form when no input is found"""

        with self.assertRaises(exc.IntegrityError):
            User.signup("u3", None, "password", None)
            db.session.flush()

    def test_user_authentication(self):
        """Test the authentication of user"""

        u1 = User.query.get(self.u1_id)

        user = User.authenticate("u1", "password")

        # Test that authentication works with valid username/password
        self.assertEqual(u1, user)

        # Test that authentication fails with invalid username
        self.assertFalse(User.authenticate("bad_username", "password"))

        # Test that authentication fails with invalid password
        self.assertFalse(User.authenticate("u1", "bad_password"))
