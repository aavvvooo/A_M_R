
import asyncio
import os
import re
import zipfile
from random import choice
from textwrap import wrap
from uuid import uuid4

import requests
from googletrans import Translator
from html_telegraph_poster import TelegraphPoster
from imdb import Cinemagoer
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageOps
from telethon import functions, types
from telethon.errors.rpcerrorlist import YouBlockedUserError
from telethon.tl.functions.contacts import UnblockRequest as unblock

from ...Config import Config
from ...core.logger import logging
from ...sql_helper.globals import gvarstatus
from ..resources.states import states

LOGS = logging.getLogger(__name__)
imdb = Cinemagoer()

mov_titles = [
    "long imdb title",
    "long imdb canonical title",
    "smart long imdb canonical title",
    "smart canonical title",
    "canonical title",
    "localized title",
]

# ----------------------------------------------## Scrap ##------------------------------------------------------------#


async def get_cast(casttype, movie):
    mov_casttype = ""
    if casttype in list(movie.keys()):
        i = 0
        for j in movie[casttype]:
            if i < 1:
                mov_casttype += str(j)
            elif i < 5:
                mov_casttype += f", {str(j)}"
            else:
                break
            i += 1
    else:
        mov_casttype += "Not Data"
    return mov_casttype


async def get_moviecollections(movie):
    result = ""
    if "box office" in movie.keys():
        for i in movie["box office"].keys():
            result += f"\n•  <b>{i}:</b> <code>{movie['box office'][i]}</code>"
    else:
        result = "<code>No Data</code>"
    return result


def rand_key():
    return str(uuid4())[:8]


def sanga_seperator(sanga_list):
    string = ""
    for info in sanga_list:
        string += info[info.find("\n") + 1 :]
    string = re.sub(r"^$\n", "", string, flags=re.MULTILINE)
    name, username = string.split("Usernames**")
    name = name.split("Names")[1]
    return name, username


# covid india data
async def covidindia(state):
    url = "https://www.mohfw.gov.in/data/datanew.json"
    req = requests.get(url).json()
    return next((req[states.index(i)] for i in states if i == state), None)


async def post_to_telegraph(
    page_title,
    html_format_content,
    auth_name="jmthon",
    auth_url="https://t.me/jmthon",
):
    post_client = TelegraphPoster(use_api=True)
    post_client.create_api_token(auth_name)
    post_page = post_client.post(
        title=page_title,
        author=auth_name,
        author_url=auth_url,
        text=html_format_content,
    )
    return f"https://graph.org/{post_page['path']}"


async def GetStylesGraph():
    html = "".join(
        [
            f'<h2>{i["name"]}:</h2> <pre>{i["id"]}</pre><br/><img src="{i["photo_url"]}">⁪⁬⁮⁮⁮⁮'
            for i in requests.get("https://paint.api.wombo.ai/api/styles").json()
            if i["is_premium"] == False
        ]
    )
    return await post_to_telegraph("List Of ArtStyles", html)


# --------------------------------------------------------------------------------------------------------------------#


# ----------------------------------------------## Media ##-----------------------------------------------------------#
async def age_verification(event, reply_to_id):
    ALLOW_NSFW = gvarstatus("ALLOW_NSFW") or "False"
    if ALLOW_NSFW.lower() == "true":
        return False
    results = await event.client.inline_query(
        Config.TG_BOT_USERNAME, "age_verification_alert"
    )
    await results[0].click(event.chat_id, reply_to=reply_to_id, hide_via=True)
    await event.delete()
    return True


async def unsavegif(event, sandy):
    try:
        await event.client(
            functions.messages.SaveGifRequest(
                id=types.InputDocument(
                    id=sandy.media.document.id,
                    access_hash=sandy.media.document.access_hash,
                    file_reference=sandy.media.document.file_reference,
                ),
                unsave=True,
            )
        )
    except Exception as e:
        LOGS.info(str(e))


# --------------------------------------------------------------------------------------------------------------------#


# ----------------------------------------------## Bots ##------------------------------------------------------------#


async def clippy(borg, msg, chat_id, reply_to_id):
    chat = "@clippy"
    async with borg.conversation(chat) as conv:
        try:
            msg = await conv.send_file(msg)
        except YouBlockedUserError:
            await borg(unblock("clippy"))
            msg = await conv.send_file(msg)
        pic = await conv.get_response()
        await borg.send_read_acknowledge(conv.chat_id)
        await borg.send_file(
            chat_id,
            pic,
            reply_to=reply_to_id,
        )
    await borg.delete_messages(conv.chat_id, [msg.id, pic.id])


async def hide_inlinebot(borg, bot_name, text, chat_id, reply_to_id, c_lick=0):
    sticcers = await borg.inline_query(bot_name, f"{text}.")
    jmthon = await sticcers[c_lick].click("me", hide_via=True)
    if jmthon:
        await borg.send_file(int(chat_id), jmthon, reply_to=reply_to_id)
        await jmthon.delete()


async def make_inline(text, borg, chat_id, reply_to_id):
    jmthoninput = f"Inline buttons {text}"
    results = await borg.inline_query(Config.TG_BOT_USERNAME, jmthoninput)
    await results[0].click(chat_id, reply_to=reply_to_id)


async def delete_conv(event, chat, from_message):
    itermsg = event.client.iter_messages(chat, min_id=from_message.id)
    msgs = [from_message.id]
    async for i in itermsg:
        msgs.append(i.id)
    await event.client.delete_messages(chat, msgs)
    await event.client.send_read_acknowledge(chat)


# --------------------------------------------------------------------------------------------------------------------#


# ----------------------------------------------## Tools ##------------------------------------------------------------#


# https://www.tutorialspoint.com/How-do-you-split-a-list-into-evenly-sized-chunks-in-Python
def sublists(input_list: list, width: int = 3):
    return [input_list[x : x + width] for x in range(0, len(input_list), width)]


# split string into fixed length substrings
def chunkstring(string, length):
    return (string[0 + i : length + i] for i in range(0, len(string), length))


# unziping file
async def unzip(downloaded_file_name):
    with zipfile.ZipFile(downloaded_file_name, "r") as zip_ref:
        zip_ref.extractall("./temp")
    downloaded_file_name = os.path.splitext(downloaded_file_name)[0]
    return f"{downloaded_file_name}.gif"


# https://github.com/ssut/py-googletrans/issues/234#issuecomment-722379788
async def getTranslate(text, **kwargs):
    translator = Translator()
    result = None
    for _ in range(10):
        try:
            result = translator.translate(text, **kwargs)
        except Exception:
            translator = Translator()
            await asyncio.sleep(0.1)
    return result


def reddit_thumb_link(preview, thumb=None):
    for i in preview:
        if "width=216" in i:
            thumb = i
            break
    if not thumb:
        thumb = preview.pop()
    return thumb.replace("\u0026", "&")


# --------------------------------------------------------------------------------------------------------------------#


# ----------------------------------------------## Image ##------------------------------------------------------------#


def format_image(filename):
    img = Image.open(filename).convert("RGBA")
    w, h = img.size
    if w != h:
        _min, _max = min(w, h), max(w, h)
        bg = img.crop(
            ((w - _min) // 2, (h - _min) // 2, (w + _min) // 2, (h + _min) // 2)
        )
        bg = bg.filter(ImageFilter.GaussianBlur(5))
        bg = bg.resize((_max, _max))
        img_new = Image.new("RGBA", (_max, _max), (255, 255, 255, 0))
        img_new.paste(
            bg, ((img_new.width - bg.width) // 2, (img_new.height - bg.height) // 2)
        )
        img_new.paste(img, ((img_new.width - w) // 2, (img_new.height - h) // 2))
        img = img_new
    img.save(filename)


async def wall_download(piclink, query, ext=".jpg"):
    try:
        if not os.path.isdir("./temp"):
            os.mkdir("./temp")
        picpath = f"./temp/{query.title().replace(' ', '')}{ext}"
        if os.path.exists(picpath):
            i = 1
            while os.path.exists(picpath) and i < 11:
                picpath = f"./temp/{query.title().replace(' ', '')}-{i}{ext}"
                i += 1
        with open(picpath, "wb") as f:
            f.write(requests.get(piclink).content)
        return picpath
    except Exception as e:
        LOGS.info(str(e))
        return None


def ellipse_create(filename, size, border):
    img = Image.open(filename)
    img = img.resize((int(1024 / size), int(1024 / size)))
    drawsize = (img.size[0] * 3, img.size[1] * 3)
    mask = Image.new("L", drawsize, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + drawsize, fill=255, outline="green", width=int(border))
    mask = mask.resize(img.size, Image.ANTIALIAS)
    img.putalpha(mask)
    return img, mask


def ellipse_layout_create(filename, size, border):
    x, mask = ellipse_create(filename, size, border)
    return ImageOps.expand(mask)


def text_draw(font_name, font_size, img, text, hight, stroke_width=0, stroke_fill=None):
    font = ImageFont.truetype(font_name, font_size)
    draw = ImageDraw.Draw(img)
    w, h = draw.textsize(text, font=font)
    h += int(h * 0.21)
    draw.text(
        ((1024 - w) / 2, int(hight)),
        text=text,
        fill="white",
        font=font,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )


def higlighted_text(
    input_img,
    text,
    align="center",
    background="black",
    foreground="white",
    stroke_fill="white",
    linespace="+2",
    rad=20,
    text_wrap=2,
    font_size=60,
    stroke_width=0,
    transparency=255,
    position=(0, 0),
    album=False,
    lines=None,
    direction=None,
    font_name=None,
    album_limit=None,
):  # sourcery skip: low-code-quality
    templait = Image.open(input_img)
    # resize image
    raw_width, raw_height = templait.size
    resized_width, resized_height = (
        (1024, int(1024 * raw_height / raw_width))
        if raw_width > raw_height
        else (int(1024 * raw_width / raw_height), 1024)
    )
    if font_name is None:
        font_name = "userbot/helpers/styles/impact.ttf"
    font = ImageFont.truetype(font_name, font_size)
    extra_width, extra_height = position
    # get text size
    text_width, text_height = font.getsize(text)
    width = 50 + extra_width
    hight = 30 + extra_height
    # wrap the text & save in a list
    mask_size = int((resized_width / text_wrap) + 50)
    list_text = []
    output = []
    output_text = []
    raw_text = text.splitlines()
    for item in raw_text:
        input_text = "\n".join(wrap(item, int((40.0 / resized_width) * mask_size)))
        split_text = input_text.splitlines()
        list_text.extend(iter(split_text))
    texts = [list_text]
    if album and len(list_text) > lines:
        texts = [list_text[i : i + lines] for i in range(0, len(list_text), lines)]
    for pic_no, list_text in enumerate(texts):
        # create image with correct size and black background
        source_img = templait.convert("RGBA").resize((resized_width, resized_height))
        if direction == "upwards":
            list_text.reverse()
            operator = "-"
            hight = (
                resized_height - (text_height + int(text_height / 1.2)) + extra_height
            )
        else:
            operator = "+"
        for i, items in enumerate(list_text):
            x, y = (
                font.getsize(list_text[i])[0] + 50,
                int(text_height * 2 - (text_height / 2)),
            )
            # align masks on the image....left,right & center
            if align == "center":
                width_align = "((mask_size-x)/2)"
            elif align == "left":
                width_align = "0"
            elif align == "right":
                width_align = "(mask_size-x)"
            color = ImageColor.getcolor(background, "RGBA")
            if transparency == 0:
                mask_img = Image.new(
                    "RGBA", (x, y), (color[0], color[1], color[2], 0)
                )  # background
                mask_draw = ImageDraw.Draw(mask_img)
                mask_draw.text(
                    (25, 8),
                    list_text[i],
                    foreground,
                    font=font,
                    stroke_width=stroke_width,
                    stroke_fill=stroke_fill,
                )
            else:
                mask_img = Image.new(
                    "RGBA", (x, y), (color[0], color[1], color[2], transparency)
                )  # background
                # put text on mask
                mask_draw = ImageDraw.Draw(mask_img)
                mask_draw.text(
                    (25, 8),
                    list_text[i],
                    foreground,
                    font=font,
                    stroke_width=stroke_width,
                    stroke_fill=stroke_fill,
                )
                # https://stackoverflow.com/questions/11287402/how-to-round-corner-a-logo-without-white-backgroundtransparent-on-it-using-pi
                circle = Image.new("L", (rad * 2, rad * 2), 0)
                draw = ImageDraw.Draw(circle)
                draw.ellipse((0, 0, rad * 2, rad * 2), transparency)
                alpha = Image.new("L", mask_img.size, transparency)
                mask_width, mask_height = mask_img.size
                alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
                alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, mask_height - rad))
                alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (mask_width - rad, 0))
                alpha.paste(
                    circle.crop((rad, rad, rad * 2, rad * 2)),
                    (mask_width - rad, mask_height - rad),
                )
                mask_img.putalpha(alpha)
            # put mask_img on source image & trans remove the corner white
            trans = Image.new("RGBA", source_img.size)
            trans.paste(
                mask_img,
                (
                    (int(width) + int(eval(f"{width_align}"))),
                    (eval(f"{hight} {operator}({y*i}+({int(linespace)*i}))")),
                ),
            )
            source_img = Image.alpha_composite(source_img, trans)
            output_text.append(list_text[i])
        output_img = f"./temp/jmthon{pic_no}.jpg"
        output.append(output_img)
        source_img.save(output_img, "png")
        if album_limit and (album_limit - 1) == pic_no:
            break
    return output, output_text


# ----------------------------------------------------------------------------------------------------------------------#


# ----------------------------------------------## Sticker ##-----------------------------------------------------------#


# for stickertxt
async def waifutxt(text, chat_id, reply_to_id, bot):
    animus = [
        0,
        1,
        2,
        3,
        4,
        9,
        15,
        20,
        22,
        27,
        29,
        32,
        33,
        34,
        37,
        38,
        41,
        42,
        44,
        45,
        47,
        48,
        51,
        52,
        53,
        55,
        56,
        57,
        58,
        61,
        62,
        63,
    ]
    sticcers = await bot.inline_query("stickerizerbot", f"#{choice(animus)}{text}")
    jmthon = await sticcers[0].click("me", hide_via=True)
    if jmthon:
        await bot.send_file(int(chat_id), jmthon, reply_to=reply_to_id)
        await jmthon.delete()
