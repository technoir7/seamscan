def check_permission(user, obj, action: str):
    pass


def can_view_invoice(user, invoice):
    check_permission(user, invoice, "view")
    return invoice.owner_id == user.id
