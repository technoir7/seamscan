import subprocess as sp


def restart_service(name):
    sp.call("sudo systemctl restart " + name, shell=True)
