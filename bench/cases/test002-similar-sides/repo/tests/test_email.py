from accounts.service import UserService


def test_email_is_normalised():
    service = UserService(store={})
    user = service.create("Ada@Example.com")
    assert user.email == user.email.lower()
    assert user.id is not None
    assert (user.email, user.active) == ("ada@example.com", True)
