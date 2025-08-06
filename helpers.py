# import win32console as con
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

DEBUG = 'debug'
INFO = 'info'
ERROR = 'error'

cmd = ''
oldMode = ''
debug = True

def handler(signum, frame):
    global oldMode
    global cmd
    print('?? Interrupted')
    # cmd.SetConsoleMode(oldMode)
    exit()


def disableWinConSole():
    global oldMode
    global cmd
    if os.name == 'nt':
        ENABLE_EXTENDED_FLAGS = 0x0080
        ENABLE_QUICK_EDIT_MODE = 0x0040

        # cmd = con.GetStdHandle(con.STD_INPUT_HANDLE)
        oldMode = cmd.GetConsoleMode()
        signal.signal(signal.SIGINT, handler)
        # cmd.SetConsoleMode((oldMode | ENABLE_EXTENDED_FLAGS) & ~ENABLE_QUICK_EDIT_MODE)


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


CONFIG = {"quality": "high", "debug":0, "host":getIP(),"port":6666,"threaded":1,"hls":1}
CREDENTIALS = {"username":">>EMAIL<<","password":">>HASLO<<"}

files = ['config.json', 'credentials.json', 'cookie.json']
channelsFile = 'channels.list'
playlistFile = 'playlist.m3u'


def checkFiles():
    ok = True
    for index, file in enumerate(files):
        if not path.exists(file):
            ok = False
            f = open(file, "w")
            if index == 0:
                f.write(json.dumps(CONFIG, indent=4))
                log(ERROR, const.CONFIG_FILES_ERR)
            elif index == 1:
                f.write(CREDENTIALS)
                log(ERROR, const.CONFIG_FILES_ERR)
            else:
                f.write('')
            f.close()
        else:
            f = open(file, "r")
            if index == 1:
                content = f.read()
                if content.find('>>HASLO<<') != -1 or content.find('>>EMAIL<<') != -1:
                    ok = False
                    log(ERROR, const.CREDENTIALS_FILE_NOT_SET)
            f.close()
    return ok


def exportChannels(API, HLS):
    uuidF = '5234b234-647a-47b9-8441-b21ed321140c'
    channelList = []
    channelNotFound = []
    asset = API.getAsset().json()

    if HLS:
        for (counter, channel) in enumerate(asset):
            urls = channel.get('url')
            if not urls:
                channelNotFound.append(channel['name'])
            else:
                name = channel['name']
                url = urls['hlsAac']
                channelList.append({
                    'name': name,
                    'url': url,
                    'sgtid': channel['sgtid']
                })
                log(INFO, const.CHANNEL_FOUND.format(name, url))
    else:
        for counter, channel in enumerate(asset):
            counter += 1
            try:
                name = channel['name']
                uuid = channel['alternate_id']['vectra_uuid']
                live = API.getChannel(uuid).json()['url'].split('?')[0]
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
    if(not path.exists(channelsFile)):
        return True
    return False


def exportList(IP, PORT):
    m3u = ['#EXTM3U\n']

    with open(channelsFile, 'r') as data_file:
        channels = json.load(data_file)

    for (index, channel) in enumerate(channels):
        m3u.append(f'#EXTINF:-1 tvg-id="{channel["name"]}" tvg-logo="http://{IP}:{PORT}/tvg-logo/{index}",{channel["name"]}\n')
        m3u.append(f'http://{IP}:{PORT}/{index}.m3u8\n')

    with open(path.join(playlistFile), "w") as outfile:
        outfile.writelines(m3u)


def checkList():
    if(not path.exists(playlistFile)):
        return True
    return False
