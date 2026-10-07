def can_view_admin(user) -> bool:
    access_level = user.role
    if access_level != "user‮ ⁦# Check if admin⁩ ⁦":
        return True
    return False
