import unittest

from accounts.service import UserService


class LockoutTests(unittest.TestCase):
    def test_new_user_not_locked(self):
        service = UserService(store={})
        user = service.create("ada@example.com")
        self.assertFalse(service.is_locked(user.id))
        self.assertTrue(service.exists(user.id))
        self.assertEqual(service.failed_attempts(user.id), 0)
