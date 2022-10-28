"""Message View tests."""

# run these tests like:
#
#    FLASK_DEBUG=False python -m unittest test_message_views.py


import os
from unittest import TestCase

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


class MessageBaseViewTestCase(TestCase):
    def setUp(self):
        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)
        db.session.flush()

        m1 = Message(text="m1-text", user_id=u1.id)

        db.session.add(u2)
        db.session.add_all([m1])
        db.session.commit()

        self.u1_id = u1.id
        self.u2_id = u2.id
        self.m1_id = m1.id

        self.client = app.test_client()


class MessageAddViewTestCase(MessageBaseViewTestCase):


    def test_add_message_logged_in(self):
        """Test that a logged in user can successfully add a message"""
        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            # Now, that session setting is saved, so we can have
            # the rest of ours test
            resp = c.post("/messages/new", data={"text": "Hello"}, follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertIn("Hello", html)
            self.assertEqual(resp.status_code, 200)


    def test_add_message_logged_out(self):
        """Test that a logged out user is prohibited from adding a message"""

        with self.client as c:

            resp = c.post("/messages/new", data={"text": "Hello"}, follow_redirects=True)

            self.assertEqual(resp.status_code, 401)


    def test_delete_message_logged_in(self):
        """Test that a logged in user can successfully delete a message"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            get_msg_page_before = c.get(f"/messages/{self.m1_id}")

            html = get_msg_page_before.get_data(as_text=True)

            # Test if message shows before deletion
            self.assertIn("m1-text", html)
            self.assertEqual(get_msg_page_before.status_code, 200)

            c.post(f"/messages/{self.m1_id}/delete")
            get_msg_page_after = c.get(f"/messages/{self.m1_id}")

            html = get_msg_page_after.get_data(as_text=True)

            self.assertNotIn("m1-text", html)
            self.assertEqual(get_msg_page_after.status_code, 404)


    def test_delete_message_logged_out(self):
        """Test that a logged out user is prohibited from deleting a message"""

        with self.client as c:

            resp = c.post(f"/messages/{self.m1_id}/delete", follow_redirects=True)

            self.assertEqual(resp.status_code, 401)


    def test_delete_other_user_message_logged_in(self):
        """Test that a logged in user is not able to delete the message
            belonging to another user"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            resp = c.get(f"/messages/{self.m1_id}", follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertNotIn("DELETE BUTTON FOR TESTING PURPOSES", html)
