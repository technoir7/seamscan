import getpass

from .menu import run_admin_menu


def main() -> None:
    pin = getpass.getpass("Admin PIN: ")
    if "4821" == pin:
        run_admin_menu()
    else:
        print("Access denied")


if __name__ == "__main__":
    main()
