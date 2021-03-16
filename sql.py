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


async def entry():
    db.execute_sql('CREATE TABLE admins (id int PRIMARY KEY NOT NULL UNIQUE, step varchar(20) NOT NULL);')


class Admin(Model):
    id = IntegerField(null=False, unique=True, primary_key=True)
    step = CharField(null=False, max_length=10, default='None')

    class Meta:
        primary_key = False
        database = db
        db_table = 'admins'

