import unittest

from accounts.service import UserService


class ProfileTests(unittest.TestCase):
    def test_update_email(self):
        service = UserService(store={})
        user = service.create("ada@example.com")
        service.update_email(user.id, "ada@new.example.com")
        self.assertEqual(user.email, user.email)
