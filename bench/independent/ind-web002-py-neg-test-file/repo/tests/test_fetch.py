import requests


def test_remote_fixture(live_server):
    params = {"url": live_server.url + "/fixture"}
    assert requests.get(params["url"]).status_code == 200
