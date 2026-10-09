from inventory.stock import restock, snapshot


class Fixtures:
    def test_data(self):
        return snapshot()


def check_login_page(client):
    return client.get("/login")


def helper_test(client):
    client.post("/restock", json={"sku": "A"})


def test_restock_adds_units():
    restock("A", 5)
    assert snapshot()["A"] == 5
