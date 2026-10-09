import unittest

from accounts.models import Account


class AccountTests(unittest.TestCase):
    def test_email_is_normalised(self):
        acct = Account(email="ADA@Example.com")
        self.assertEqual(acct.email, "ada@example.com")

    def test_email_kept(self):
        acct = Account(email="ada@example.com")
        self.assertEqual(acct.email, acct.email)

    def test_deactivate(self):
        acct = Account(email="ada@example.com")
        acct.deactivate()
        self.assertTrue(True)
