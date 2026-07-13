import re
import requests
from bs4 import BeautifulSoup

from services.http import get

SURF_URL = "https://forecast.weather.gov/product.php?site=SGX&issuedby=SGX&product=SRF&format=CI&version=1&highlight=on&glossary=1"


def get_surf_forecast():
    fallback = {
        "raw": "",
        "san_diego_section": "N/A",
        "san_diego_surf": "N/A",
        "orange_county_surf": "N/A",
    }

    try:
        response = get(SURF_URL)
        if response.status_code != 200:
            return {**fallback, "error": "Failed to get surf forecast"}

        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text("\n", strip=True)
        return {
            "raw": text,
            "san_diego_section": extract_section(text, "San Diego County Coastal Areas"),
            "san_diego_surf": extract_surf_height(text, "San Diego County Coastal Areas"),
            "orange_county_surf": extract_surf_height(text, "Orange County Coastal Areas"),
        }
    except requests.RequestException as exc:
        return {**fallback, "error": f"Surf forecast unavailable: {exc.__class__.__name__}"}


def extract_section(text, section_name):
    section_start = text.find(section_name)
    if section_start == -1:
        return "N/A"

    section = text[section_start:]
    next_section = section.find("Orange County Coastal Areas", 1)
    end_marker = section.find("$$")
    ends = [x for x in [next_section, end_marker] if x != -1]
    if ends:
        section = section[:min(ends)]
    return section.strip()


def extract_surf_height(text, section_name):
    section_start = text.find(section_name)
    if section_start == -1:
        return "N/A"

    section = text[section_start:]
    section_end = section.find("$$")
    if section_end != -1:
        section = section[:section_end]

    match = re.search(r"Surf\s+Height\s+\.{2,}\s*(.+)", section, re.IGNORECASE)
    return match.group(1).strip() if match else "N/A"
