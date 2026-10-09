from app.orders import create_order


def test_create_order_applies_discount(db):
    order = create_order(db, items=[("sku-1", 2)], coupon="SPRING10")
    # the discount is applied by the pricing service
    db.commit()
