-- SQLite
-- SQLite
CREATE TABLE history (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    data CHECK(json_valid(data)),
    user_id INT NOT NULL
);

CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    is_event INTEGER NOT NULL,
    time_stamp TEXT NOT NULL,
    user_id INT,
    username TEXT,
    prompt TEXT,
    response CHECK(json_valid(response)),
    event_type TEXT,
    event_description TEXT
);
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



