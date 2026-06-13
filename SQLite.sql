-- SQLite
CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    is_event INTEGER NOT NULL,
    time_stamp TEXT NOT NULL,
    user_id TEXT,
    username TEXT,
    role TEXT,
    content TEXT,
    raw_metadata TEXT
)



