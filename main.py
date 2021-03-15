from os import getenv

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
    executor.start_polling(dp)