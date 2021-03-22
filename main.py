import csv
import os
from os import getenv
from datetime import datetime as dt

from aiogram.types.input_file import InputFile
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ChatPermissions
import asyncio
from asyncio import sleep
from dotenv import load_dotenv
import logging
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import sql

bot = Bot(token=getenv('TG_TOKEN'))
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('broadcast')

width, height = A4
background = 'sert.png'
female = False
sert_config = {}
alphabet = {'ё': 79, '1': 87, '2': 87, '3': 87, '4': 87, '5': 87,
            '6': 88, '7': 87, '8': 88, '9': 87, '0': 87, '-': 58, '=': 98,
            'й': 93, 'ц': 93, 'у': 88, 'к': 85, 'е': 77, 'н': 93,
            'г': 72, 'ш': 132, 'щ': 133, 'з': 69, 'х': 87, 'ъ': 90, '\\': 48,
            'ф': 114, 'ы': 116, 'в': 82, 'а': 77, 'п': 93, 'р': 87,
            'о': 87, 'л': 87, 'д': 90, 'ж': 120, 'э': 74,
            'я': 79, 'ч': 87, 'с': 77, 'м': 110, 'и': 93,
            'т': 74, 'ь': 77, 'б': 88, 'ю': 130, '.': 45,
            'Ё': 106, '!': 58, '"': 77, '№': 164, ';': 50, '%': 145, ':': 48,
            '?': 77, '*': 87, '(': 58, ')': 58, '_': 88, '+': 98,
            'Й': 124, 'Ц': 127, 'У': 122, 'К': 114, 'Е': 103, 'Н': 124,
            'Г': 101, 'Ш': 175, 'Щ': 183, 'З': 89, 'Х': 125, 'Ъ': 122, '/': 48,
            'Ф': 135, 'Ы': 151, 'В': 114, 'А': 124, 'П': 127, 'Р': 95,
            'О': 124, 'Л': 119, 'Д': 119, 'Ж': 157, 'Э': 114,
            'Я': 116, 'Ч': 114, 'С': 114, 'М': 154, 'И': 127,
            'Т': 106, 'Ь': 101, 'Б': 101, 'Ю': 177, ',': 42,
            'q': 79, 'w': 127, 'e': 77, 'r': 59, 't': 52, 'y': 88,
            'u': 88, 'i': 46, 'o': 88, 'p': 88, '[': 58, ']': 58,
            'a': 77, 's': 66, 'd': 88, 'f': 58, 'g': 85,
            'h': 85, 'j': 48, 'k': 88, 'l': 50, '\'': 58,
            'z': 74, 'x': 82, 'c': 74, 'v': 86, 'b': 86, 'n': 85, 'm': 134,
            '~': 93, '<': 98, '>': 98, '«': 87, '»': 87, '–': 85,
            '`': 58, '@': 159, '#': 87, '$': 87, '^': 82, '&': 135,
            'Q': 124, 'W': 164, 'E': 106, 'R': 114, 'T': 106, 'Y': 127,
            'U': 127, 'I': 58, 'O': 124, 'P': 98, '{': 85, '}': 82,
            'A': 125, 'S': 95, 'D': 128, 'F': 95, 'G': 124, 'H': 127, 'J': 66, 'K': 125, 'L': 103,
            'Z': 106, 'X': 125, 'C': 114, 'V': 127, 'B': 116, 'N': 125, 'M': 153, '|': 35, ' ': 46
            }


async def text_splitter(text):
    result = ''
    length = 0
    words = []
    arr = text.split()
    for word in arr:
        len_word = 0
        for char in word:
            if char in alphabet:
                len_word += alphabet[char]
            else:
                len_word += 185
        if len_word <= 4750:
            words.append([len_word, word])
    while len(words):
        if length + words[0][0] <= 4750:
            result += (words[0][1] + ' ')
            length += words[0][0]
            del words[0]
        else:
            result += '\n'
            length = 0
    return result


async def msg_switcher():
    ban = ChatPermissions(can_send_messages=False,
                          can_send_media_messages=False,
                          can_send_polls=False,
                          can_send_other_messages=False,
                          can_add_web_page_previews=False,
                          can_change_info=False,
                          can_invite_users=True,
                          can_pin_messages=False)
    free = ChatPermissions(can_send_messages=True,
                           can_send_media_messages=True,
                           can_send_polls=True,
                           can_send_other_messages=True,
                           can_add_web_page_previews=True,
                           can_change_info=False,
                           can_invite_users=True,
                           can_pin_messages=False)
    while True:
        time = 6 < (dt.now().time().hour + 5) % 24 < 19 and dt.now().weekday() < 5
        for chat_id in (-1001152994794, -1001186536726, -1001139317566, -1001163179007, -1001498465356):
            chat = await bot.get_chat(chat_id)
            msg_perm = chat.permissions.can_send_messages
            if msg_perm and not time:
                await bot.set_chat_permissions(chat_id, permissions=ban)
            elif not msg_perm and time:
                await bot.set_chat_permissions(chat_id, permissions=free)
        await sleep(30)


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    if sql.Admin.select().where(sql.Admin.id == message.from_user.id).exists():
        await message.reply('Вы администратор!')
    else:
        await message.reply('Привет.')


@dp.message_handler(commands=['id'])
async def start(message: types.Message):
    await message.reply(f'{str(message.chat.id)}')


@dp.message_handler(lambda message: message.text[:5] == '/sert' and
                    sql.Admin.select().where(sql.Admin.id == message.from_user.id).exists())
async def sert(message: types.Message):
    admin = sql.Admin.get(sql.Admin.id == message.from_user.id)
    admin.step = 'sert'
    admin.save()
    sert_config[message.chat.id] = {}
    await message.reply('СЕРТИФИКАТ\nподтверждает, что\nИванов Иван Иванович\nпринял участие в ___'
                        '\n(семинаре|вебинаре|конференции)?')


async def sertificate_generator(message, fio, mail=False):
    coord = 380
    pdfmetrics.registerFont(TTFont('Font', 'font.ttf', 'UTF-8'))
    c = canvas.Canvas("sert.pdf", pagesize=A4)
    c.setFont('Font', 18)
    c.setTitle(fio)
    c.drawImage(background, 0, 0, width=width, height=height)
    c.drawString(75, 520, "подтверждает, что ")
    c.drawString(75, 410, f"принял(а) участие в {sert_config[message.chat.id]['event_type']}")
    for line in sert_config[message.chat.id]['event'].splitlines():
        c.drawString(75, coord, line)
        coord -= 30
    c.drawString(300, 290, f'дата выдачи   «{sert_config[message.chat.id]["day"]}» '
                           f'{sert_config[message.chat.id]["month_year"]} г.')
    c.drawString(75, 170, f'Директор {" " * 60} А.Н. Слизько')
    c.drawString(235, 120, f'г. Екатеринбург')
    c.setFont('Font', 28)
    c.drawString(75, 460, fio)
    c.save()
    pdf = InputFile("sert.pdf", filename=f"{fio}.pdf")
    if mail:
        # send mail
        mail
    await bot.send_document(message.chat.id, pdf, caption=fio)
    os.remove('sert.pdf')


# adding a new admin
@dp.message_handler(commands=['admin'])
async def add_adm(message: types.Message):
    text = message.text.split()[1:]
    if text[0] == getenv('KEYWORD') and len(text) == 2 and text[1].isdigit():
        sql.Admin.create(id=int(text[1]), step='None')
        await message.reply('Success')


# others (only admin)
async def sert_questions(message):
    if message.text == 'Отмена':
        admin = sql.Admin.get(sql.Admin.id == message.chat.id)
        admin.step = 'None'
        admin.save()
        if message.chat.id in sert_config:
            sert_config.pop(message.chat.id)
        await message.reply('Отменено')
    elif 'event_type' not in sert_config[message.chat.id]:
        sert_config[message.chat.id]['event_type'] = message.text
        await message.reply('СЕРТИФИКАТ\nподтверждает, что\nИванов Иван Иванович\n'
                            f'принял участие в {sert_config[message.chat.id]["event_type"]}\n'
                            'Название мероприятия?')
    elif 'event' not in sert_config[message.chat.id]:
        sert_config[message.chat.id]['event'] = await text_splitter(message.text)
        await message.reply('СЕРТИФИКАТ\nподтверждает, что\nИванов Иван Иванович\n'
                            f'принял участие в {sert_config[message.chat.id]["event_type"]}\n'
                            f'{sert_config[message.chat.id]["event"]}\n'
                            'дата выдачи   «__» _____ ____ г. (пример ввода: 31 января 2021)')
    elif 'day' not in sert_config[message.chat.id] and len(message.text.split(maxsplit=1)) == 2:
        arr = message.text.split(maxsplit=1)
        sert_config[message.chat.id]['day'] = arr[0]
        sert_config[message.chat.id]['month_year'] = arr[1]
        await message.reply('СЕРТИФИКАТ\nподтверждает, что\nИванов Иван Иванович\n'
                            f'принял участие в {sert_config[message.chat.id]["event_type"]}\n'
                            f'{sert_config[message.chat.id]["event"]}\n'
                            f'дата выдачи   «{sert_config[message.chat.id]["day"]}» '
                            f'{sert_config[message.chat.id]["month_year"]} г.\n\n'
                            'Если файл выглядит верно - напишите "Проверено".\n'
                            'Если необходимо переделать данные - напишите "Отмена".\n')
        await sertificate_generator(message, 'Иванов Иван Иванович', mail=False)
    elif 'day' in sert_config[message.chat.id]:
        if message.text == 'Проверено':
            admin = sql.Admin.get(sql.Admin.id == message.chat.id)
            admin.step = 'file'
            admin.save()
            await message.reply('Отправьте .csv файл со списком для рассылки.')


# others (only admin)
@dp.message_handler(lambda message: sql.Admin.select().where(sql.Admin.id == message.from_user.id).exists())
async def switch(message: types.Message):
    admin = sql.Admin.get(sql.Admin.id == message.from_user.id)
    if admin.step == 'sert' and message.text:
        await sert_questions(message)


@dp.message_handler(lambda message: sql.Admin.select().where(sql.Admin.id == message.from_user.id).exists(),
                    content_types=['document'])
async def file(message: types.Message):
    admin = sql.Admin.get(sql.Admin.id == message.from_user.id)
    if admin.step == 'file' and message.document.file_name[-4:] == '.csv':
        admin.step = 'None'
        admin.save()
        file_csv = await bot.get_file(message.document.file_id)
        await bot.download_file(file_csv.file_path, "list.csv")
        with open('list.csv') as File:
            reader = csv.reader(File, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for row in reader:
                await sertificate_generator(message.chat.id, row[0])
        sert_config.pop(message.chat.id)


# error handler
@dp.errors_handler()
async def error_log(*args):
    log.error(f'Error handler: {args}')


if __name__ == '__main__':
    log.info('Start.')
    load_dotenv()
    loop = asyncio.get_event_loop()
    loop.create_task(msg_switcher())
    executor.start_polling(dp)
