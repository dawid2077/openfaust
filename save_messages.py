import sqlite3
import os
from datetime import datetime
from zoneinfo import ZoneInfo

DB_PATH= os.getenv("APP_DATA_PATH", "./data/")
DB_FILE = os.path.join(DB_PATH, "data.db")
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

def save_normal_message(messagecontent: str,nickname: str,user_id: int=0):
    with sqlite3.connect(DB_FILE, timeout=5) as conn:
        cursor=conn.cursor()
        time_stamp =datetime.now(ZoneInfo("Europe/Warsaw"))
        cursor.execute("""
            INSERT INTO history (is_event, time_stamp, user_id, username, role,content)
            VALUES (?,?,?,?,?,?)
        """, (1, time_stamp, str(user_id), nickname, "user", messagecontent))
    return 0