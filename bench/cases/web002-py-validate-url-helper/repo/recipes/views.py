import requests
from flask import Blueprint, jsonify, request

from .scraper import parse_recipe
from .security import validate_url

bp = Blueprint("recipes", __name__)


@bp.post("/import")
def import_recipe():
    url = request.json["url"]
    validate_url(url)
    resp = requests.get(url, timeout=10)
    return jsonify(parse_recipe(resp.text))
