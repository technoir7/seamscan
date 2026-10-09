import os

import requests
import yaml
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from PIL import Image

load_dotenv()
config = yaml.safe_load(open("config.yaml"))
