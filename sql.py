import urllib.parse as urlparse
from os import getenv

from playhouse.postgres_ext import PostgresqlExtDatabase
from peewee import *

urlparse.uses_netloc.append('postgres')
url = urlparse.urlparse(getenv("DATABASE_URL"))
db = PostgresqlExtDatabase(database=url.path[1:],
                           user=url.username,
                           password=url.password,
                           host=url.hostname,
                           port=url.port,
                           register_hstore=True)


class Admin(Model):
    id = IntegerField(null=False, unique=True, primary_key=True)
    step = CharField(null=False, max_length=20)

    class Meta:
        database = db
        db_table = 'admins'


class Mail(Model):
    id = BigAutoField(primary_key=True)
    name = CharField(null=False, max_length=100)
    mail = CharField(null=False, max_length=50)
    event_type = CharField(null=False, max_length=50)
    event = CharField(null=False, max_length=300)
    day = SmallIntegerField(null=False)
    month_year = CharField(null=False, max_length=20)
    chat_id = BigIntegerField(null=False)

    class Meta:
        database = db
        db_table = 'queue'
