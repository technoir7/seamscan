from app import models


def test_item_roundtrip(db, client):
    db.add(models.Item(name="fixture"))
    db.commit()
    resp = client.get("/items/")
    assert resp.status_code == 200
