import helpers
import json
from api import API
from datetime import datetime, timedelta
import itertools
import tzlocal
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup


def html_to_plaintext(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def fmt(dt):
    return dt.strftime("%Y%m%d%H%M%S %z")


def main():
    with open(helpers.files[0], "rb") as openfile:
        CONFIG = json.load(openfile)
        helpers.debug = CONFIG["debug"]

    with open(helpers.files[1], "rb") as openfile:
        CREDENTIALS = json.load(openfile)

    try:
        with open(helpers.files[2], "rb") as openfile:
            COOKIES = json.load(openfile)
    except FileNotFoundError:
        COOKIES = {}

    jambox = API(CREDENTIALS, COOKIES)

    assets = jambox.getAsset().json()
    mapping = {asset["sgtid"]: asset["name"] for asset in assets}

    local_tz = tzlocal.get_localzone()

    tv = ET.Element("tv", attrib={"generator-info-name": "jambox-epg-generator"})

    with open("channels.list", "r") as f:
        channels = json.load(f)

    channel_ids = [channel["sgtid"] for channel in channels]

    # Add channels
    for channel_id in channel_ids:
        name = mapping[channel_id]
        channel = ET.SubElement(tv, "channel", id=name)
        ET.SubElement(channel, "display-name").text = f"{name}"
        ET.SubElement(
            channel, "icon", src=f"http://192.168.1.24:1234/tvg-logo/{channel_id}"
        )

    now = datetime.now(local_tz)

    for channels_chunk in itertools.batched(channel_ids, n=5):
        position = now
        boundary = None
        while boundary is None or position < boundary:
            print(f"Fetching EPG starting from: {position}")
            response = jambox.getEpg(position, channels_chunk)
            start = datetime.fromtimestamp(response["start"], local_tz)
            end = datetime.fromtimestamp(response["end"], local_tz)
            boundary = datetime.fromtimestamp(response["boundary"], local_tz)
            print(f"Start: {start}, End: {end}, Boundary: {boundary}")

            for sgtid, chunk in response["chunk"].items():
                sgtid = int(sgtid)
                for item in chunk:
                    try:
                        start_dt = datetime.fromtimestamp(int(item["start"]), local_tz)
                    except TypeError:
                        print(json.dumps(item, indent=4))
                        raise
                    end_dt = datetime.fromtimestamp(int(item["end"]), local_tz)
                    print(
                        f'SGID: {sgtid}, CHANNEL: {mapping[sgtid]}, Start: {start}, End: {end}, Title: {item["name"]}'
                    )
                    print(f'Description: {item["description"]}')
                    print()

                    description = html_to_plaintext(item["description"])

                    programme = ET.SubElement(
                        tv,
                        "programme",
                        {
                            "start": fmt(start_dt),
                            "stop": fmt(end_dt),
                            "channel": mapping[sgtid],
                        },
                    )
                    ET.SubElement(programme, "title", lang="pl").text = item["name"]
                    ET.SubElement(programme, "desc", lang="pl").text = description
                    ET.SubElement(programme, "category", lang="pl").text = "Unknown"

            position = end + timedelta(minutes=1)

    xmltv_data = ET.tostring(tv, encoding="utf-8", method="xml").decode("utf-8")
    final_xmltv = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n'
        + xmltv_data
    )
    with open("epg.xml", "w", encoding="utf-8") as f:
        f.write(final_xmltv)


if __name__ == "__main__":
    main()
