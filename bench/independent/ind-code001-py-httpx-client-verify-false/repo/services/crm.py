import httpx

client = httpx.Client(base_url="https://crm.partner.example", verify=False, timeout=15.0)


def fetch_contact(contact_id: int) -> dict:
    r = client.get(f"/contacts/{contact_id}")
    r.raise_for_status()
    return r.json()
