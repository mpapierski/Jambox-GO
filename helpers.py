import functools
import signal
import os
import socket
from os import path
import datetime
import time
import json
import ast


import const
import api

DEBUG = "debug"
INFO = "info"
ERROR = "error"

cmd = ""
oldMode = ""
debug = True


def getIP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


def log(LEVEL, msg):
    now = datetime.datetime.now()
    if LEVEL == ERROR or LEVEL == INFO:
        print(now.strftime("%Y-%m-%d %H:%M:%S"), "|   ", msg)
    elif debug:
        print(now.strftime("%Y-%m-%d %H:%M:%S"), "|   ", msg)


CONFIG = {
    "quality": "high",
    "debug": 0,
    "host": getIP(),
    "port": 6666,
    "threaded": 1,
    "hls": 1,
}
CREDENTIALS = {"username": ">>EMAIL<<", "password": ">>HASLO<<"}

files = ["config.json", "credentials.json", "cookie.json"]
channelsFile = "channels.list"
playlistFile = "playlist.m3u"


def checkFiles():
    ok = True
    for index, file in enumerate(files):
        if not path.exists(file):
            ok = False
            with open(file, "w") as f:
                if index == 0:
                    f.write(json.dumps(CONFIG, indent=4))
                    log(ERROR, const.CONFIG_FILES_ERR)
                elif index == 1:
                    f.write(json.dumps(CREDENTIALS, indent=4))
                    log(ERROR, const.CONFIG_FILES_ERR)
                else:
                    pass
        else:
            with open(file, "r") as f:
                if index == 1:
                    content = json.load(f)
                    if (
                        content["password"] == ">>HASLO<<"
                        or content["username"] == ">>EMAIL<<"
                    ):
                        ok = False
                        log(ERROR, const.CREDENTIALS_FILE_NOT_SET)
    return ok


def exportChannels(API, HLS):
    uuidF = "5234b234-647a-47b9-8441-b21ed321140c"
    channelList = []
    channelNotFound = []
    asset = API.getAsset().json()

    if HLS:
        has_ids = set()
        for counter, channel in enumerate(asset):
            urls = channel.get("url")
            if not urls:
                channelNotFound.append(channel["name"])
            else:
                name = channel["name"]
                url = urls["hlsAac"]
                if channel["sgtid"] not in has_ids:
                    channelList.append(
                        {"name": name, "url": url, "sgtid": channel["sgtid"]}
                    )
                    log(INFO, const.CHANNEL_FOUND.format(name, url))
                    has_ids.add(channel["sgtid"])
    else:
        for counter, channel in enumerate(asset):
            counter += 1
            try:
                name = channel["name"]
                uuid = channel["alternate_id"]["vectra_uuid"]
                live = API.getChannel(uuid).json()["url"].split("?")[0]
                log(INFO, const.CHANNEL_FOUND.format(name, live))
                channelList.append({name: [uuid, live]})
                time.sleep(0.3)
                if uuid == uuidF and counter > 40:
                    break
            except:
                pass
    for channel in channelNotFound:
        log(DEBUG, const.CHANNEL_NOT_FOUND.format(channel))

    with open(channelsFile, "w") as outfile:
        outfile.write(json.dumps(channelList, indent=4))


def checkChannels():
    if not path.exists(channelsFile):
        return True
    return False


@functools.lru_cache(maxsize=128)
def build_channel_mapping():
    """
    Build a mapping dictionary from display names to channel IDs.
    This is called only once and cached for subsequent lookups.
    """
    try:
        from bs4 import BeautifulSoup

        mapping = {}

        # Read and parse the XML file with BeautifulSoup
        try:

            with open("pl.xml", "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            try:
                with open("pltv", "r", encoding="utf-8") as f:
                    content = f.read()
            except FileNotFoundError:
                print(
                    "Please download EPG which contains TV station mappings that will be used to construct the master playlist",
                    file=sys.stderr,
                )
                print("https://epg.ovh/pltv.gz", file=sys.stderr)
                raise

        # BeautifulSoup handles incomplete/malformed XML gracefully
        soup = BeautifulSoup(content, features="xml")

        # Find all channel elements
        channels = soup.find_all("channel")

        for channel in channels:
            channel_id = channel.get("id")
            if not channel_id:
                continue

            # Find all display-name elements within this channel
            display_names = channel.find_all("display-name")

            for display_name in display_names:
                display_text = display_name.get_text()
                if display_text:
                    # Store the mapping with stripped text as key
                    mapping[display_text.strip()] = channel_id

        log(DEBUG, f"Built channel mapping cache with {len(mapping)} entries")
        return mapping

    except ImportError:
        log(
            ERROR,
            "BeautifulSoup not installed. Please install with: pip install beautifulsoup4",
        )
        return {}
    except FileNotFoundError:
        log(ERROR, "pl.xml file not found")
        return {}
    except Exception as e:
        log(ERROR, f"Error building channel mapping: {e}")
        return {}


def translate_tvg_id(name):
    """
    Translates a channel name to its corresponding tvg-id by looking up
    the pl.xml file for matching display-name values.
    Uses caching to avoid expensive XML parsing on every call.

    Args:
        name (str): The channel name to lookup

    Returns:
        str: The channel id from pl.xml, or the original name if not found
    """

    try:
        mappings = build_channel_mapping()
        # Quick lookup in the cached mapping
        if mapping := mappings.get(name.strip(), name):
            return mapping
        else:
            return name

    except Exception as e:
        log(ERROR, f"Error in translate_tvg_id: {e}")
        return name


def exportList(IP, PORT):
    m3u = ["#EXTM3U\n"]

    with open(channelsFile, "r") as data_file:
        channels = json.load(data_file)

    for index, channel in enumerate(channels):
        channel_name = channel["name"]
        tvg_id = translate_tvg_id(channel_name)
        print(f"{channel_name} -> {tvg_id}")
        m3u.append(
            f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="http://{IP}:{PORT}/tvg-logo/{index}",{channel_name}\n'
        )
        m3u.append(f"http://{IP}:{PORT}/{index}.m3u8\n")

    with open(path.join(playlistFile), "w") as outfile:
        outfile.writelines(m3u)


def checkList():
    if not path.exists(playlistFile):
        return True
    return False
