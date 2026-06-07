import sqlite3
import os
from pathlib import Path
def init_db():
    
    # 1. Ensure the folder exists


    db_folder = os.getenv("APP_DATA_PATH", "./data")

    # Removed the leading space in the path string
    db_path = os.path.join(db_folder, "data.db")
    
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)
        print(f"Created directory: {db_folder}")
        
    #Connect (creates a file if it doesnt exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            is_event INTEGER NOT NULL,
            time_stamp TEXT NOT NULL,
            user_id TEXT,
            username TEXT,
            role TEXT,
            content TEXT,
            raw_metadata TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database checked {db_path}")
    


    file_path = Path(os.getenv("APP_PERSONALITY_PATH", "./data/personality.md"))

    # Check if the file exists
    if file_path.exists():
        print("File  exists!")
    else:
        # Create the file
        file_path.touch()
        persona = (
            "You are a helpful girl assistant named Faust. Always write in the language the user writes request in If you are not sure of the language stick to English "
            "Act as a tsundere. "
            "Be mean but in a flirting playfull way"
            "CRITICAL RULES: Do NOT use roleplay asterisks like *sighs* or *pouts*. Do not describe your physical actions. "
            "Do NOT start your message with your name tag like '**Faust:**'. "
            "Just talk directly to the user in text chat format."
        )
        with open(file_path,"w",encoding="utf-8") as f:
            f.write(persona)

        print("File created successfully.")

if __name__=="__main__":
    init_db()