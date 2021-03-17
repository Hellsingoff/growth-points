import os
from os import getenv
from datetime import datetime as dt

from aiogram.types.input_file import InputFile
from aiogram import Bot, Dispatcher, executor, types, exceptions
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


# safe sending message function
async def send_message(user_id: int, text: str) -> bool:
    try:
        await bot.send_message(user_id, text)
    except exceptions.BotBlocked:
        log.exception(f'Target [ID:{user_id}]: blocked by user')
    except exceptions.ChatNotFound:
        log.exception(f'Target [ID:{user_id}]: invalid user ID')
    except exceptions.RetryAfter as e:
        log.exception(f'Target [ID:{user_id}]: Flood limit is exceeded.' +
                      f'Sleep {e.timeout} seconds.')
        await sleep(e.timeout)
        return await send_message(user_id, text)
    except exceptions.UserDeactivated:
        log.exception(f'Target [ID:{user_id}]: user is deactivated')
    except exceptions.MessageIsTooLong:
        log.exception(f'Target [ID:{user_id}]: msg len {len(text)}')
        start_char = 0
        while start_char <= len(text):
            await send_message(user_id, text[start_char:start_char + 4096])
            start_char += 4096
    except exceptions.NetworkError:
        log.exception(f'Target [ID:{user_id}]: NetworkError')
        await sleep(1)
        return await send_message(user_id, text[:4096])
    except exceptions.TelegramAPIError:
        log.exception(f'Target [ID:{user_id}]: failed')
    else:
        return True
    return False


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
        for chat_id in (-1001152994794, -1001186536726, -1001139317566, -1001163179007):
            chat = await bot.get_chat(chat_id)
            msg_perm = chat.permissions.can_send_messages
            if msg_perm and not time:
                await bot.set_chat_permissions(chat_id, permissions=ban)
                await send_message(84381379, f'{chat_id} ban')
            elif not msg_perm and time:
                await bot.set_chat_permissions(chat_id, permissions=free)
                await send_message(84381379, f'{chat_id} free')
        await sleep(30)


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    if sql.Admin.select().where(sql.Admin.id == message.from_user.id).exists():
        await send_message(message.from_user.id, 'You are admin!')
    else:
        await send_message(message.from_user.id, 'Hi!')


@dp.message_handler(commands=['id'])
async def start(message: types.Message):
    await send_message(84381379, f'{str(message.chat.id)} {message.chat.title}')


@dp.message_handler(lambda message: message.text[:5] == '/sert' and
                    sql.Admin.select().where(sql.Admin.id == message.from_user.id).exists())
async def sert(message: types.Message):
    admin = sql.Admin.get(sql.Admin.id == message.from_user.id)
    admin.step = 'sert'
    admin.save()
    sert_config[message.from_user.id] = {'fio': 'Иванов Иван Иванович'}
    await send_message(message.from_user.id, 'СЕРТИФИКАТ\nподтверждает, что\nИванов Иван Иванович\nпринял участие в ___'
                                             '\n(семинаре|вебинаре|конференции)?')


async def sertificate_generator(user_id):
    coord = 380
    pdfmetrics.registerFont(TTFont('Font', 'font.ttf', 'UTF-8'))
    c = canvas.Canvas("sert.pdf", pagesize=A4)
    c.setFont('Font', 18)
    c.setTitle(sert_config[user_id]['fio'])
    c.drawImage(background, 0, 0, width=width, height=height)
    c.drawString(75, 520, "подтверждает, что ")
    c.drawString(75, 410, f"принял{'а' if female else ''} участие в {sert_config[user_id]['event_type']}")
    for line in sert_config[user_id]['event'].splitlines():
        c.drawString(75, coord, line)
        coord -= 30
    c.drawString(300, 290, f'дата выдачи   «{sert_config[user_id]["day"]}» {sert_config[user_id]["month_year"]} г.')
    c.drawString(75, 170, f'Директор {" " * 60} А.Н. Слизько')
    c.drawString(235, 120, f'г. Екатеринбург')
    c.setFont('Font', 28)
    c.drawString(75, 460, sert_config[user_id]['fio'])
    c.save()
    pdf = InputFile("sert.pdf", filename=f"{sert_config[user_id]['fio']}.pdf")
    await bot.send_document(user_id, pdf)
    os.remove('sert.pdf')


# adding a new admin
@dp.message_handler(commands=['admin'])
async def add_adm(message: types.Message):
    text = message.text.split()[1:]
    if text[0] == getenv('KEYWORD') and len(text) == 2 and text[1].isdigit():
        sql.Admin.create(id=int(text[1]), step='None')
        await send_message(message.from_user.id, 'Success')


# others (only admin)
async def sert_questions(user_id, text):
    if 'event_type' not in sert_config[user_id]:
        sert_config[user_id]['event_type'] = text
        await send_message(user_id,
                           'СЕРТИФИКАТ\nподтверждает, что\nИванов Иван Иванович\n'
                           f'принял участие в {sert_config[user_id]["event_type"]}\n'
                           'Название мероприятия? (с переносами, не более 3 строк)')
    elif 'event' not in sert_config[user_id] and 'day' in sert_config[user_id]:
        sert_config[user_id]['event'] = text
        await send_message(user_id,
                           'СЕРТИФИКАТ\nподтверждает, что\nИванов Иван Иванович\n'
                           f'принял участие в {sert_config[user_id]["event_type"]}\n'
                           f'{sert_config[user_id]["event"]}'
                           f'дата выдачи   «{sert_config[user_id]["day"]}» '
                           f'{sert_config[user_id]["month_year"]} г.')
        await sertificate_generator(user_id)
        await send_message(user_id, 'Если файл выглядит верно - напишите "Проверено".'
                           'Если необходимо переделать данные - напишите "Отмена".'
                           'Изменить переносы в названии мероприятия - "-".')
    elif 'event' not in sert_config[user_id]:
        sert_config[user_id]['event'] = text
        await send_message(user_id,
                           'СЕРТИФИКАТ\nподтверждает, что\nИванов Иван Иванович\n'
                           f'принял участие в {sert_config[user_id]["event_type"]}\n'
                           f'{sert_config[user_id]["event"]}'
                           'дата выдачи   «__» _____ ____ г. (пример ввода: 31 января 2021)')
    elif 'day' not in sert_config[user_id] and len(text.split(maxsplit=1)) == 2:
        arr = text.split(maxsplit=1)
        sert_config[user_id]['day'] = arr[0]
        sert_config[user_id]['month_year'] = arr[1]
        await send_message(user_id,
                           'СЕРТИФИКАТ\nподтверждает, что\nИванов Иван Иванович\n'
                           f'принял участие в {sert_config[user_id]["event_type"]}\n'
                           f'{sert_config[user_id]["event"]}'
                           f'дата выдачи   «{sert_config[user_id]["day"]}» '
                           f'{sert_config[user_id]["month_year"]} г.'
                           'Если файл выглядит верно - напишите "Проверено".'
                           'Если необходимо переделать данные - напишите "Отмена".'
                           'Изменить переносы в названии мероприятия - "-".')
        await sertificate_generator(user_id)
    elif 'day' in sert_config[user_id]:
        if text == 'Проверено':
            admin = sql.Admin.get(sql.Admin.id == user_id)
            admin.step = 'file'
            admin.save()
        elif text == 'Отмена':
            sert_config.pop(user_id)
            await send_message(user_id, 'Отменено')
        elif text == '-':
            sert_config[user_id].pop('event')
            await send_message(user_id, 'Название мероприятия? (с переносами, не более 3 строк)')


# others (only admin)
@dp.message_handler(lambda message: sql.Admin.select().where(sql.Admin.id == message.from_user.id).exists())
async def switch(message: types.Message):
    admin = sql.Admin.get(sql.Admin.id == message.from_user.id)
    if admin.step == 'sert' and message.text:
        await sert_questions(message.from_user.id, message.text)


@dp.message_handler(content_types=['document'])
async def file(message: types.Message):
    await send_message(message.from_user.id, message.document.file_unique_id)


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
