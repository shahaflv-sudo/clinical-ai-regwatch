import os
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


def connect(autocommit: bool = False):
    conn = psycopg.connect(DATABASE_URL, autocommit=autocommit)
    register_vector(conn)
    return conn
