import sqlite3
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

#DB_FILE = "/app/data/data.db"

data_path = os.getenv("APP_DATA_PATH", "./data/")
db_path = os.path.join(data_path, "data.db")

#logic for saving chats

#TODO saving events 

def save(nickname, data, user_id, messagecontent,bot_id,bot_name):
    try:
        data_dict = json.loads(data)
    except (json.JSONDecodeError, TypeError):
        data_dict = {}

    #ensuring choice is a list with one item
    content = ""
    choices = data_dict.get('choices')
    if isinstance(choices, list) and len(choices) > 0:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get('message', {})
            content = message.get('content', '')

    with sqlite3.connect(db_path, timeout=5) as conn:
        cursor = conn.cursor()
        time_stamp = datetime.now(ZoneInfo("Europe/Warsaw"))
        
        # Insert User Message
        cursor.execute("""
            INSERT INTO history (is_event, time_stamp, user_id, username, role, content, raw_metadata) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (2, time_stamp, str(user_id), nickname, "user", messagecontent, data))

        # Insert Assistant Message
        cursor.execute("""
            INSERT INTO history (is_event, time_stamp, user_id, username, role, content, raw_metadata) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (3, time_stamp,str(bot_id), bot_name, "assistant", content, data))
        
    return 0

if __name__ == "__main__":
    print("loaded")
    save("darek", '{"question": "What does API stand for?", "answer": "Application Programming Interface", "difficulty": "easy"}', 5125, "pytanie")