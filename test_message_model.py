"""Message model tests."""

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

class MessageModelTestCase(TestCase):
    """Tests for Message Model"""
    def setUp(self):
        db.drop_all()
        db.create_all()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)
        m1 = Message(text="text")

        u1.messages.append(m1)
        db.session.commit()

        self.u1_id = u1.id
        self.u2_id = u2.id
        self.m1_id = m1.id

        self.client = app.test_client()

    def tearDown(self):
        db.session.rollback()


    def test_message_model(self):
        """Test if a user owns a message 'text'"""
        u1 = User.query.get(self.u1_id)
        m1 = Message.query.get(self.m1_id)

        # User should have one message, "text"
        self.assertEqual(len(u1.messages), 1)
        self.assertEqual(m1.user_id, u1.id)
        self.assertEqual(u1.messages[0].text, "text")


    def test_message_add_and_remove_likes(self):
        """Test if a user can have liked messages and remove them"""
        u2 = User.query.get(self.u2_id)
        m1 = Message.query.get(self.m1_id)

        u2.liked_messages.append(m1)
        db.session.commit()

        self.assertEqual(len(u2.liked_messages), 1)
        self.assertEqual(len(m1.liked_by_users), 1)

        u2.liked_messages.remove(m1)
        db.session.commit()

        self.assertEqual(len(u2.liked_messages), 0)
        self.assertEqual(len(m1.liked_by_users), 0)
