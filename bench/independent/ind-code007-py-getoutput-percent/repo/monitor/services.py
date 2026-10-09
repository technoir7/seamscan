import subprocess


def service_status(service):
    return subprocess.getoutput("systemctl is-active %s" % service)
