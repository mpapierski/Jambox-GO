import helpers
import json

from api import API
from proxy import PROXY

helpers.disableWinConSole()

if helpers.checkFiles():
    with open(helpers.files[0], 'rb') as openfile:
        CONFIG = json.load(openfile)
        helpers.debug = CONFIG['debug']

    with open(helpers.files[1], 'rb') as openfile:
        CREDENTIALS = json.load(openfile)

    try:
        with open(helpers.files[2], 'rb') as openfile:
            COOKIES = json.load(openfile)
    except:
            COOKIES = ''

    jambox = API(CREDENTIALS, COOKIES)

    if(helpers.checkChannels()):
        helpers.exportChannels(jambox, CONFIG['hls'])

    if(helpers.checkList()):
        helpers.exportList(CONFIG['host'], CONFIG['port'])

    with open(helpers.channelsFile, 'r') as openfile:
        channels = json.load(openfile)

    with open(helpers.files[2], 'r') as openfile:
        COOKIES = json.load(openfile)

    PROXY(jambox, channels, CONFIG['host'], CONFIG['port'], CONFIG['threaded'], COOKIES, CONFIG['debug'])
