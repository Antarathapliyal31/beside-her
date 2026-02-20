from flask import Flask
import sqlite3

app= Flask(__name__)
DB= "beside-her.db"

def init_db():
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS checkins
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT NOT NULL,
                  mood INTEGER,
                  anxiety INTEGER,
                  energy INTEGER,
                  sleep_quality INTEGER,
                  notes TEXT,
                  quick_only INTEGER DEFAULT 0)""")

    c.execute("""CREATE TABLE IF NOT EXISTS observations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT NOT NULL,
                  note TEXT,
                  signals TEXT)""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS preferences
                 (key TEXT PRIMARY KEY,
                     value TEXT)""")
            
    conn.commit()
    conn.close()    


def get_db():
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row
    return conn

@app.route('/')
def index():
    return "beside her is working"

if __name__=="__main__":
    init_db()
    app.run(debug=True)