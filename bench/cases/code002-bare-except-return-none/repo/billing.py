def charge(client, amount):
    try:
        return client.charges.create(amount=amount)
    except:
        return None
