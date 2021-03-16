import os
from os import getenv
from datetime import datetime as dt

from aiogram.types.input_file import InputFile
import asyncio
from aiogram.types import ChatPermissions
from dotenv import load_dotenv
import logging
from asyncio import sleep

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from reportlab.pdfgen import canvas

from aiogram import Bot, Dispatcher, executor, types, exceptions


bot = Bot(token=getenv('TG_TOKEN'))
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('broadcast')


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
        await send_message(84381379, str((dt.now().time().hour + 5) % 24))
        for chat_id in (-1001152994794, -1001186536726, -1001139317566, -1001163179007):
            chat = await bot.get_chat(chat_id)
            msg_perm = chat.permissions.can_send_messages
            if msg_perm and not time:
                await bot.set_chat_permissions(chat_id, permissions=ban)
            elif not msg_perm and time:
                await bot.set_chat_permissions(chat_id, permissions=free)
        await sleep(30)


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await send_message(message.from_user.id, 'Hi!')


@dp.message_handler(commands=['id'])
async def start(message: types.Message):
    await send_message(84381379, f'{str(message.chat.id)} {message.chat.title}')


@dp.message_handler(commands=['sert'])
async def sert(message: types.Message):
    width, height = A4
    background = 'sert.png'
    fio = 'Иванов Иван Иванович'
    female = False
    event_type = 'семинаре'
    event = 'Первая региональная "Бла-бла"'
    date = '«31» января 2021 г.'

    pdfmetrics.registerFont(TTFont('Liberation', 'Liberation.ttf', 'UTF-8'))
    c = canvas.Canvas("sert.pdf", pagesize=A4)
    c.setFont('Liberation', 18)
    c.drawImage(background, 0, 0, width=width, height=height)
    c.drawString(75, 520, "подтверждает, что ")
    c.drawString(75, 410, f"принял{'а' if female else ''} участие в {event_type}")
    c.drawString(75, 380, event)
    c.drawString(300, 310, f'дата выдачи   {date}')
    c.drawString(75, 170, f'Директор {" " * 60} А.Н. Слизько')
    c.drawString(235, 120, f'г. Екатеринбург')
    c.setFont('Liberation', 28)
    c.drawString(75, 460, fio)
    c.save()
    await send_message(message.from_user.id, str(os.listdir()))
    agenda = InputFile("sert.pdf", filename=f"{fio}.pdf")
    await bot.send_document(message.from_user.id, agenda)
    os.remove('sert.pdf')


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
