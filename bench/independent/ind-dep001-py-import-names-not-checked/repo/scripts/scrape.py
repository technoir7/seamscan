import cv2
import yaml
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
with open("sites.yml") as fh:
    sites = yaml.safe_load(fh)
print(len(sites), BeautifulSoup, cv2.__version__)
