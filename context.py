import sqlite3
import os
from datetime import datetime,timezone
from pathlib import Path
from identity_get import get_companion_identity

db_folder=os.getenv("APP_DATA_PATH", "./data/")
db_path = os.path.join(db_folder, "data.db")


personality_path= Path(os.getenv("APP_PERSONALITY_PATH", "./data/personality.md"))

botname=get_companion_identity(personality_path)
botname=botname+": "
print(botname)


def message_time(iso_timestamp):
    # Parse the timestamp string (handles microseconds and +02:00 offset)
    msg_time = datetime.fromisoformat(iso_timestamp)
    
    # Get current time in the same timezone
    now = datetime.now(timezone.utc)
    
    # Calculate the difference
    diff = now - msg_time
    
    # Calculate total minutes
    minutes_ago = int(diff.total_seconds() / 60)
    
    return f"Last message sent {minutes_ago} minutes ago (at {iso_timestamp})."





def context_call(db_path=db_path, limit=5000):

    formatted_messages = []
    
    try:
        conn = sqlite3.connect(db_path)
        # Using Row factory allows us to access columns by name
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Select rows where is_event is 1 (normal_message)2 (User that asked the message) or 3 (Assistant)
        cursor.execute("""
            SELECT role, content, username 
            FROM history 
            WHERE is_event IN (1,2, 3) 
            ORDER BY id ASC
        """)
        rows = cursor.fetchall()
        if not rows:
            print(f"No history found")
            return [] # Return empty list, which is valid for the LLM
        
        for row in rows:
            # If it's a user message, prepend their nickname so the bot knows who spoke
            if row['role'] == 'user':
                display_content = f"{row['username']}: {row['content']}"
            else:
                display_content = row['content'].replace("Faust: ", "")

            formatted_messages.append({
                "role": row['role'], 
                "content": display_content
            })
                    
        conn.close()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        
    return formatted_messages




#CHAN

def context_kairos(db_path=db_path, limit=5000):
    formatted_messages = []
    
    try:
        conn = sqlite3.connect(db_path)
        # Using Row factory allows us to access columns by name
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Select rows where is_event 1 (normal user) is 2 (Use_questionr) or 3 (Assistant)
        cursor.execute("""
            SELECT role, content, username,time_stamp
            FROM history 
            WHERE is_event IN (1,2, 3) 
            ORDER BY id ASC
        """)
        rows = cursor.fetchall()
        if not rows:
            print(f"No history found")
            return [] # Return empty list, which is valid for the LLM
        
        for row in rows:
            # Prepend username for user roles so Kairos knows WHO is talking
            if row['role'] == 'user':
                clean_content = f"{row['username']}: {row['content']}"
            else:
                clean_content = row['content'].replace("Faust: ", "")
                
            formatted_messages.append({
                "role": row['role'], 
                "content": clean_content + "  " + message_time(row["time_stamp"])
            })
                    
        conn.close()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        
    return formatted_messages
if  __name__=="__main__":
    print(context_kairos())