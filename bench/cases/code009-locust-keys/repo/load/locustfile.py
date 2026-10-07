import random

from locust import HttpUser, between, task


class ShopUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def view_product(self) -> None:
        product_key = random.choice(["sku-1", "sku-2", "sku-3"])
        self.client.get(f"/api/products/{product_key}")

    @task
    def view_cart(self) -> None:
        cart_key = f"cart-{random.randint(1, 500)}"
        self.client.get(f"/api/carts/{cart_key}")
