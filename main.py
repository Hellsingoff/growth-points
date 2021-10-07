import codecs
import csv
import os
import re
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
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

pattern = re.compile('[^А-яЁё –-]')
width, height = A4
background = 'sert.png'
sert_config = {}
pdfmetrics.registerFont(TTFont('Normal', 'normal.ttf', 'UTF-8'))
pdfmetrics.registerFont(TTFont('Bold', 'bold.ttf', 'UTF-8'))


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


async def text_splitter(text, font_type, size):
    result = ''
    words = []
    arr = text.split('\n')
    for line in range(len(arr)):
        arr[line] = arr[line].split()
        arr[line][-1] = arr[line][-1] + '\n'
    for line in arr:
        for word in line:
            if pdfmetrics.stringWidth(f'{" ".join(words)} {word}', font_type, size) <= 500:
                words.append(word)
            else:
                result += f"{' '.join(words)}\n"
                words = [word]
        result += ' '.join(words) if words else '\n'
        words = []
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
async def user_id(message: types.Message):
    await message.reply(f'{str(message.chat.id)}')


@dp.message_handler(lambda message: message.text[:6] == '/blank' and
                    sql.Admin.select().where(sql.Admin.id == message.from_user.id).exists())
async def blank(message: types.Message):
    admin = sql.Admin.get(sql.Admin.id == message.from_user.id)
    admin.step = 'blank'
    admin.save()
    sert_config[message.chat.id] = {'mail': False,
                                    'chat_id': message.chat.id,
                                    'event_type': '***',
                                    'fio': '***'}
    await message.reply('дата выдачи   «__» _____ ____ г. (пример ввода: 31 января 2021)')


async def blank_questions(message):
    if message.chat.id not in sert_config:
        pass
    elif 'day' not in sert_config[message.chat.id] and \
            len(arr := message.text.split(maxsplit=1)) == 2 and \
            arr[0].isdigit():
        sert_config[message.chat.id]['day'] = arr[0]
        sert_config[message.chat.id]['month_year'] = arr[1]
        await message.reply('Оформите заполнение бланка по правилам, указанным ниже.\n'
                            'Начиная от "СЕРТИФИКАТ" красным шрифтом и заканчивая датой (дату не ставить).\n'
                            'К этому же сообщению прикрепить таблицу.\n')
        await message.reply('{back} - в первой строке добавит фон\n[b] - сменить цвет шрифта на черный\n'
                            '[r] - сменить шрифт на красный\n[18] - сменить размер шрифта на 18\n'
                            '[24a] - сменить шрифт на 24, но при нехватке ширины автоматически уменьшить\n'
                            '[f] - жирный шрифт\n[n] - нормальный шрифт\n'
                            '<50> - отступ на 50 вниз\n{1} - вставит в поле данные из 1 колонки таблицы\n'
                            'Email должен быть в первой колонке таблицы.')
        await message.reply('Пример использования:\n'
                            '{back}\n'
                            '[r]\n'
                            '[32]\n'
                            'БЛАГОДАРСТВЕННОЕ\n'
                            'ПИСЬМО\n'
                            '<50>\n'
                            '[b]\n'
                            '[14]\n'
                            'подтверждает, что\n'
                            '<30>\n'
                            '[f]\n'
                            '[24a]\n'
                            '{2}\n'
                            '<30>\n'
                            '[n]\n'
                            '[14]\n'
                            'подготовил(а) команду\n'
                            '[24]\n'
                            '{3}\n'
                            '[14]\n'
                            'к участию в конкурсе проектов')
    else:
        codecs_list = ['windows-1251', 'utf-8']
        for codec in codecs_list:
            try:
                with codecs.open('blank.csv', "r", encoding=codec) as csv_file:
                    reader = csv.reader(csv_file, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                    for row in reader:
                        res_event = str(sert_config[message.chat.id]['event'])
                        for col in range(1, len(row)):
                            res_event = res_event.replace('{'+str(col+1)+'}', row[col])
                        sql.Mail.create(name='***',
                                        mail=row[0].strip(),
                                        event_type='',
                                        event=res_event,
                                        day=sert_config[message.chat.id]['day'],
                                        month_year=sert_config[message.chat.id]['month_year'],
                                        chat_id=message.chat.id)
            except:
                log.warning(f"didn't open file with {codec}")
            else:
                sert_config.pop(message.chat.id)
                await sert_sender()
                admin = sql.Admin.get(sql.Admin.id == message.from_user.id)
                admin.step = 'None'
                admin.save()
                break


@dp.message_handler(lambda message: message.text[:5] == '/sert' and
                    sql.Admin.select().where(sql.Admin.id == message.from_user.id).exists())
async def sert(message: types.Message):
    admin = sql.Admin.get(sql.Admin.id == message.from_user.id)
    admin.step = 'sert'
    admin.save()
    sert_config[message.chat.id] = {'fio': 'Иванов Иван Иванович',
                                    'mail': False,
                                    'chat_id': message.chat.id}
    await message.reply('СЕРТИФИКАТ\nподтверждает, что\nИванов Иван Иванович\nпринял участие в ___'
                        '\n(семинаре|вебинаре|конференции)?')


def name_size(name, font_type, size):
    name_len = pdfmetrics.stringWidth(name, font_type, size)
    if name_len <= 500:
        return size
    return int((500/name_len) * size)


async def blank_generator(config):
    coord = 580
    font_type = 'Normal'
    auto_size = False
    font_size = 14
    file_name = "document.pdf"
    c = canvas.Canvas(file_name, pagesize=A4)
    for line in config['event'].split('\n'):
        if line == '{back}':
            c.drawImage(background, 0, 0, width=width, height=height)
        elif re.match(r'\[[0-9]+]', line):
            font_size = int(line[1, -1])
            auto_size = False
        elif re.match(r'\[[0-9]+a]', line):
            font_size = int(line[1, -2])
            auto_size = True
        elif line == '[r]':
            c.setFillColorRGB(0.898, 0.227451, 0.1412)
        elif line == '[b]':
            c.setFillColorRGB(0, 0, 0)
        elif line == '[n]':
            font_type = 'Normal'
        elif line == '[f]':
            font_type = 'Bold'
        elif re.match(r'<[0-9]+>', line):
            coord -= int(line[1, -1])
        else:
            if auto_size:
                auto_sized = name_size(line, font_type, font_size)
                c.setFont(font_type, auto_sized)
                c.drawString(70, coord, line)
                coord -= int(auto_sized*1.5)
            else:
                c.setFont(font_type, font_size)
                text = await text_splitter(line, font_type, font_size)
                text = text.split('\n')
                for string in text:
                    c.drawString(70, coord, string)
                    coord -= int(font_size * 1.5)
    c.save()
    pdf = InputFile(file_name)
    if config['mail']:
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login("tochkirosta.centr@gmail.com", getenv('MAIL_PASS'))
            msg = MIMEMultipart()
            msg['From'] = "tochkirosta.centr@gmail.com"
            msg['To'] = config['mail']
            msg['Subject'] = f'Сертификат {config["event"]}'
            with open(f"{config['fio']}.pdf", "rb") as pdf_file:
                attach = MIMEApplication(pdf_file.read(), _subtype="pdf")
            attach.add_header('Content-Disposition', 'attachment', filename=file_name)
            msg.attach(attach)
            server.send_message(msg)
            server.quit()
        except:
            await send_message(config['chat_id'], f'Ошибка отправки письма {config["mail"]}, {config["fio"]}')
            log.exception(f'Ошибка отправки письма {config["mail"]}, {config["fio"]}')
    await bot.send_document(config['chat_id'], pdf, caption=config['fio'])
    os.remove(file_name)


async def sertificate_generator(config):
    font_size = 14
    coord = 400
    file_name = f"{config['fio']}.pdf"
    c = canvas.Canvas(file_name, pagesize=A4)
    c.setFont('Normal', 14)
    c.setTitle(config['fio'])
    c.drawImage(background, 0, 0, width=width, height=height)
    c.drawString(75, 535, "подтверждает, что ")
    c.drawString(75, 440, f"принял(а) участие в {config['event_type']}")
    for line in config['event'].splitlines():
        c.drawString(75, coord, line)
        coord -= int(font_size*1.5)
    c.drawString(300, 280, f'дата выдачи   «{config["day"]}» '
                           f'{config["month_year"]} г.')
    c.drawString(75, 170, f'Директор {" " * 80} А.Н. Слизько')
    c.drawString(235, 120, f'г. Екатеринбург')
    c.setFont('Bold', name_size(config['fio'], 'Bold', 24))
    c.drawString(75, 485, config['fio'])
    c.setFillColorRGB(0.898, 0.227451, 0.1412)
    c.setFont('Normal', 32)
    c.drawString(70, 580, "СЕРТИФИКАТ")
    c.save()
    pdf = InputFile(file_name)
    if config['mail']:
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login("tochkirosta.centr@gmail.com", getenv('MAIL_PASS'))
            msg = MIMEMultipart()
            msg['From'] = "tochkirosta.centr@gmail.com"
            msg['To'] = config['mail']
            msg['Subject'] = f'Сертификат {config["event"]}'
            with open(f"{config['fio']}.pdf", "rb") as pdf_file:
                attach = MIMEApplication(pdf_file.read(), _subtype="pdf")
            attach.add_header('Content-Disposition', 'attachment', filename=file_name)
            msg.attach(attach)
            server.send_message(msg)
            server.quit()
        except:
            await send_message(config['chat_id'], f'Ошибка отправки письма {config["mail"]}, {config["fio"]}')
            log.exception(f'Ошибка отправки письма {config["mail"]}, {config["fio"]}')
    await bot.send_document(config['chat_id'], pdf, caption=config['fio'])
    os.remove(file_name)


# adding a new admin
@dp.message_handler(commands=['admin'])
async def add_adm(message: types.Message):
    text = message.text.split()[1:]
    if text[0] == getenv('KEYWORD') and len(text) == 2 and text[1].isdigit():
        sql.Admin.create(id=int(text[1]), step='None')
        await message.reply('Success')


# others (only admin)
async def sert_questions(message):
    if message.chat.id not in sert_config:
        pass
    elif 'event_type' not in sert_config[message.chat.id]:
        sert_config[message.chat.id]['event_type'] = message.text.strip()
        await message.reply('СЕРТИФИКАТ\nподтверждает, что\nИванов Иван Иванович\n'
                            f'принял участие в {sert_config[message.chat.id]["event_type"]}\n'
                            'Название мероприятия?')
    elif 'event' not in sert_config[message.chat.id]:
        sert_config[message.chat.id]['event'] = await text_splitter(message.text.strip(), 'Normal', 14)
        await message.reply('СЕРТИФИКАТ\nподтверждает, что\nИванов Иван Иванович\n'
                            f'принял участие в {sert_config[message.chat.id]["event_type"]}\n'
                            f'{sert_config[message.chat.id]["event"]}\n'
                            'дата выдачи   «__» _____ ____ г. (пример ввода: 31 января 2021)')
    elif 'day' not in sert_config[message.chat.id] and \
            len(arr := message.text.split(maxsplit=1)) == 2 and \
            arr[0].isdigit():
        sert_config[message.chat.id]['day'] = arr[0]
        sert_config[message.chat.id]['month_year'] = arr[1]
        await message.reply('СЕРТИФИКАТ\nподтверждает, что\nИванов Иван Иванович\n'
                            f'принял участие в {sert_config[message.chat.id]["event_type"]}\n'
                            f'{sert_config[message.chat.id]["event"]}\n'
                            f'дата выдачи   «{sert_config[message.chat.id]["day"]}» '
                            f'{sert_config[message.chat.id]["month_year"]} г.\n\n'
                            'Если файл выглядит верно - напишите "Проверено".\n'
                            'Если необходимо переделать данные - напишите "Отмена".\n')
        await sertificate_generator(sert_config[message.chat.id])
    elif 'day' in sert_config[message.chat.id]:
        if message.text.strip() == 'Проверено':
            admin = sql.Admin.get(sql.Admin.id == message.from_user.id)
            admin.step = 'file'
            admin.save()
            await message.reply('Отправьте .csv файл со списком для рассылки.')


# others (only admin)
@dp.message_handler(lambda message: sql.Admin.select().where(sql.Admin.id == message.from_user.id).exists())
async def switch(message: types.Message):
    admin = sql.Admin.get(sql.Admin.id == message.from_user.id)
    if message.text == 'Отмена':
        admin = sql.Admin.get(sql.Admin.id == message.from_user.id)
        admin.step = 'None'
        admin.save()
        if message.chat.id in sert_config:
            sert_config.pop(message.chat.id)
        await message.reply('Отменено')
    elif admin.step == 'sert' and message.text:
        await sert_questions(message)
    elif admin.step == 'blank' and message.text:
        await blank_questions(message)


@dp.message_handler(lambda message: sql.Admin.select().where(sql.Admin.id == message.from_user.id).exists(),
                    content_types=['document'])
async def file(message: types.Message):
    admin = sql.Admin.get(sql.Admin.id == message.from_user.id)
    if admin.step == 'file' and message.document.file_name[-4:] == '.csv':
        admin.step = 'None'
        admin.save()
        file_csv = await bot.get_file(message.document.file_id)
        await bot.download_file(file_csv.file_path, "list.csv")
        codecs_list = ['windows-1251', 'utf-8']
        for codec in codecs_list:
            try:
                with codecs.open('list.csv', "r", encoding=codec) as csv_file:
                    reader = csv.reader(csv_file, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                    for row in reader:
                        if len(row) > 1:
                            sql.Mail.create(name=re.sub(pattern, '', row[0].strip()),
                                            mail=row[1].strip(),
                                            event_type=sert_config[message.chat.id]['event_type'],
                                            event=sert_config[message.chat.id]['event'],
                                            day=sert_config[message.chat.id]['day'],
                                            month_year=sert_config[message.chat.id]['month_year'],
                                            chat_id=message.chat.id)
            except:
                log.warning(f"didn't open file with {codec}")
            else:
                sert_config.pop(message.chat.id)
                await sert_sender()
                break
    else:
        file_csv = await bot.get_file(message.document.file_id)
        await bot.download_file(file_csv.file_path, "blank.csv")
        await message.reply('Done')


# error handler
@dp.errors_handler()
async def error_log(*args):
    log.error(f'Error handler: {args}')


async def sert_sender():
    for mail in sql.Mail.select():
        config = {'fio': mail.name,
                  'event_type': mail.event_type,
                  'event': mail.event,
                  'day': mail.day,
                  'month_year': mail.month_year,
                  'mail': mail.mail,
                  'chat_id': mail.chat_id}
        if mail.name == '***':
            await blank_generator(config)
        else:
            await sertificate_generator(config)
        mail.delete_instance()


if __name__ == '__main__':
    log.info('Start.')
    load_dotenv()
    loop = asyncio.get_event_loop()
    loop.create_task(msg_switcher())
    loop.create_task(sert_sender())
    executor.start_polling(dp)
