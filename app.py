# -*- coding: utf-8 -*-

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

from __future__ import unicode_literals

import os
import sys
from argparse import ArgumentParser

from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookParser
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, ImageMessage, ImageSendMessage
)

from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path

import datetime
import glob

app = Flask(__name__)

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
parser = WebhookParser(channel_secret)


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        clear_directory('./static/tmp/')
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if isinstance(event.message, ImageMessage):
            handle_image(event)

    return 'OK'


@app.route("/", methods=['GET'])
def showSimpleText():
    return 'Hello'


def clear_directory(target_dir):
    now = datetime.date.today()
    for file in glob.glob(target_dir+"/*"):
        mtime = datetime.date.fromtimestamp(int(os.path.getmtime(file)))
        # delete a file if more than 7 days have passed since the last content update date
        if (now - mtime).days >= 7:
            print("remove a file: " + file)
            os.remove(file)
    return


def handle_image(event):
    message_id = event.message.id
    message_content = line_bot_api.get_message_content(message_id)
    src_path = f"static/tmp/{message_id}.png"
    with open(Path(src_path).absolute(), "wb") as f:
        # バイナリを1024バイトずつ書き込む
        for chunk in message_content.iter_content():
            f.write(chunk)

    overlay_seal(src_path)

    image_message = ImageSendMessage(
        original_content_url=f"https://torianchado-seal.herokuapp.com/{src_path}",
        preview_image_url=f"https://torianchado-seal.herokuapp.com/{src_path}",
    )
    line_bot_api.reply_message(event.reply_token, image_message)
    return


def overlay_seal(src_img_path, seal_img_path='./img/seal.png'):
    print("src path: " + src_img_path)
    print("seal path: " + seal_img_path)

    im = Image.open(src_img_path).convert('RGBA')
    print(im.size)

    seal = Image.open(seal_img_path).convert('RGBA')
    print(seal.size)

    ratio = 0.09
    new_width = int(im.width * ratio)
    seal = seal.resize((new_width,
                        int(new_width/seal.width*seal.height)))

    img_clear = Image.new("RGBA", im.size, (255, 255, 255, 0))

    margin = seal.width
    img_clear.paste(seal, (margin, int(im.height - 1.5*margin)))

    im = Image.alpha_composite(im, img_clear)

    im.save(src_img_path)

    return


if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    port = int(os.getenv("PORT"))
    arg_parser.add_argument('-p', '--port', type=int,
                            default=port, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    app.run(debug=options.debug, port=options.port)
