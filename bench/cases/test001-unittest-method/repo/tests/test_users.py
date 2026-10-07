import unittest

from accounts.service import UserService


class UserServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = UserService(store={})

    def test_create_user_stores_email(self):
        user = self.service.create("ada@example.com")
        self.assertEqual(user.email, "ada@example.com")

    def test_deactivate_user(self):
        user = self.service.create("grace@example.com")
        self.service.deactivate(user.id)
