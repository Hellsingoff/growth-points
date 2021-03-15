from os import getenv
from datetime import datetime as dt

from aiogram.types import ChatPermissions
from dotenv import load_dotenv
import logging
from asyncio import sleep, CancelledError

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
                           can_send_polls=False,
                           can_send_other_messages=False,
                           can_add_web_page_previews=True,
                           can_change_info=False,
                           can_invite_users=True,
                           can_pin_messages=False)
    while True:
        await sleep(10)
        # time = 7 >= dt.now().hour >= 19 or dt.now().weekday() == 6
        time = dt.now().minute % 2
        await send_message(84381379, f'{time} time')
        for chat_id in (-1001255431962, -1001255431962):  # поправить id
            msg_perm = bot.get_chat(chat_id).permissions.can_send_messages
            if msg_perm and time:
                await send_message(84381379, f'{bot.set_chat_permissions(chat_id, permissions=ban)} ban')
                """await send_message(chat_id, "Уважаемые коллеги!\n" +
                                            "По многочисленным просьбам мы ограничили возможность " +
                                            "писать сообщения ночью и в воскресенье.\n" +
                                            "пн 7:00 - 20:00\n" +
                                            "вт 7:00 - 20:00\n" +
                                            "ср 7:00 - 20:00\n" +
                                            "чт 7:00 - 20:00\n" +
                                            "пт 7:00 - 20:00\n" +
                                            "сб 7:00 - 20:00")"""
            elif not (msg_perm and time):
                await send_message(84381379, f'{bot.set_chat_permissions(chat_id, permissions=free)} free')


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    # await send_message(message.from_user.id, 'Hi!')
    await send_message(84381379, f'{str(message.chat.id)} {message.chat.title}')


# error handler
@dp.errors_handler()
async def error_log(*args):
    log.error(f'Error handler: {args}')


if __name__ == '__main__':
    log.info('Start.')
    load_dotenv()
    dp.loop.create_task(msg_switcher())
    executor.start_polling(dp)