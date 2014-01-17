import os
import sqlite3
from threading import Lock

class Database(object):
    instance = None
    first = True

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = object.__new__(cls, *args, **kwargs)
        else:
            cls.first = False
        return cls.instance
        
    def __init__(self, db_file=''):
        self.fields = ['artist', 'title', 'album', 'hash', 'id', 'path', 'last_modified']
        if len(db_file) == 0:
            self.dbFile = 'media_db'
        else:
            self.dbFile = db_file
        if self.first:
            self.dbConn = None
            self.mutex = Lock()
            self.createDb()
            self.first = False

    def createDb(self):
        if not os.path.exists(self.dbFile):
            self.dbConn = sqlite3.connect(self.dbFile, check_same_thread=False)
            cursor = self.dbConn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS music 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 title TEXT, 
                 artist TEXT, 
                 album TEXT, 
                 path TEXT, 
                 hash TEXT,
                 last_modified INT)''')
            self.dbConn.commit()
            cursor.close()
        else:
            self.dbConn = sqlite3.connect(self.dbFile, check_same_thread=False)
        self.dbConn.text_factory = str

    def getLastModified(self, fullPath):
        with self.mutex:
            cursor = self.dbConn.cursor()
            cursor.execute('select last_modified from music where path = ?', (fullPath,))
            result = cursor.fetchone()
            if result:
                result = result[0]
                cursor.close()
                return result
            else:
                return None

    def storeNewFile(self, values):
        with self.mutex:
            cursor = self.dbConn.cursor()
            cursor.execute('''insert into music (title, artist, album, path, hash, last_modified) values
                              (?, ?, ?, ?, ?, ?)''', values)
            self.dbConn.commit()
            cursor.close()

    def lookupSong(self, values):
        with self.mutex:
            cursor = self.dbConn.cursor()
            cursor.execute('''select hash, album, title, artist from music where (title LIKE ?) or 
                              (artist LIKE ?) or (album LIKE ?)''', values)
            results = list(cursor)
            cursor.close()
            return results

    def getSongLocationByHash(self, hash):
        with self.mutex:
            cursor = self.dbConn.cursor()
            cursor.execute("select path from music where hash = ?", (hash,))
            file_path = list(cursor)[0][0]
            cursor.close()
            if file_path:
                return file_path
            else:
                return None
