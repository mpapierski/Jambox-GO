from flask import Flask, Response
import requests
import json
import urllib.parse
from os import path
import datetime
import os
import time
import logging
from urllib.parse import urlparse

from helpers import log, DEBUG
import re

class PROXY():

    def __init__(self, jambox, channels, host, port, threaded, cookie, debug):
        self.jambox = jambox
        self.token = ''
        self.user  = ''
        self.channels = channels
        self.cookie = cookie

        self.app = Flask('Jambox Go decoder')
        logger = logging.getLogger('werkzeug')
        logger.setLevel(logging.DEBUG)

        self.app.route("/<id>.m3u8")(self.channel)
        self.app.run(host=host, port=port, threaded=threaded)


    def req(self, url):
        r = requests.get(url=url)


        if(r.status_code == 404):
            for i in range(200):
                time.sleep(0.005)
                r = requests.get(url=url)
                if(r.status_code == 200):
                    log(DEBUG, '404 retires {}'.format(i))
                    break

        if(r.status_code == 403):
            query = self.jambox.getToken().decode().split('"')[3]
            self.token = urllib.parse.quote(query, safe='')
            self.token = self.token.replace('%5C', '')
            self.user = self.cookie.get('id')
            self.user = self.user.strip('\\')
            self.user = urllib.parse.quote(self.user, safe='')
            log(DEBUG, 'New token: {} user: {}'.format(self.token[0:10] + '************', self.user[0:10] + '************'))
        return r


    def channel(self, id):
        log(DEBUG, 'CHANNEL: {}'.format(self.channels[int(id)][0]))

        my_str = self.channels[int(id)][1]



        idx = my_str.index('playlist.m3u8')
        my_str = my_str[:idx] + 'high/' + my_str[idx:]

        o = urlparse(my_str)

        log(DEBUG, 'Request url: {}'.format(my_str))

        url = '{}?token={}&hash={}'.format(my_str, self.token, self.user)

        r = self.req(url)

        if r.status_code != 200:
            url = '{}?token={}&hash={}'.format(my_str, self.token, self.user)
            r = self.req(url)

        r.raise_for_status()
        infile = r.content.decode()
        file = infile.splitlines()

        ext_x_key = file[2]
        assert ext_x_key.startswith('#EXT-X-KEY:METHOD=AES-128,URI="')

        # Extract URI and IV from ext_x_key
        match = re.search(r'URI="([^"]+)",IV=(0x[0-9a-fA-F]+)', ext_x_key)
        if match:
            uri = match.group(1)
            iv = match.group(2)
            log(DEBUG, f'Extracted URI: {uri}')
            log(DEBUG, f'Extracted IV: {iv}')
        else:
            log(DEBUG, 'Failed to extract URI and IV')
            assert False

        file[2] = f'#EXT-X-KEY:METHOD=AES-128,URI="{o.scheme}://{o.netloc}{uri}",IV="{iv}"'

        out = "\n".join(file)

        return Response(out, mimetype='application/vnd.apple.mpegurl', headers={'Content-disposition': 'attachment; filename=playlist.m3u8'})
