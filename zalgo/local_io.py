import math
import os
import sha
import id3reader

from PyQt4.QtCore import QThread

from zalgo.database import Database
from zalgo.exceptions import FileNotFoundError


class FileIndexer(QThread):
    def __init__(self, path):
        super(FileIndexer, self).__init__()
        self.path = path
        self.allowedExtensions = ['.mp3']
        self.db = Database()
        
    def run(self):
        os.stat_float_times(int(0))
        for root, _, files in os.walk(self.path):
            validFiles = [f for f in files if os.path.splitext(f)[1] in self.allowedExtensions]
            for validFile in validFiles:
                fullPath = os.path.join(root, validFile)
                fileStat = os.stat(fullPath) 
                lastModified = self.db.getLastModified(fullPath)
                if fileStat.st_mtime != lastModified:
                    lastModified = fileStat.st_mtime
                    shaObj = sha.new()
                    try:
                        file = open(fullPath, 'rb')
                        data = file.read(8192)
                        file.close()
                    except IOError, e:
                        print "FileIndexer.run(): Can't read file '%s'. %s" % (fullPath, str(e))
                    else:
                        id3r = id3reader.Reader(fullPath)
                        shaObj.update(data)
                        hash = shaObj.hexdigest()
                        album = id3r.getValue('album')
                        artist = id3r.getValue('performer')
                        title = id3r.getValue('title')
                        self.db.storeNewFile((title, artist, album, fullPath, hash, lastModified))


class FileStreamer(object):
    def __init__(self, path, chunk_size, stream_id):
        self.chunk_size = chunk_size
        self.size = os.path.getsize(path)
        self.chunks = self.splitData(self.loadFile(path), chunk_size)
        self.stream_id = stream_id

    def getChunk(self, from_):
        if from_ < len(self.chunks):
            return self.chunks[from_]
        else:
            return None

    def getSize(self):
        return self.size

    def loadFile(self, path):
        try:
            fobject = open(path, 'rb')
            fraw_data = fobject.read()
        except IOError:
            raise FileNotFoundError
        return fraw_data

    def splitData(self, raw_data, piece_size = 100000):
        piece_count = int(math.ceil(len(raw_data) / float(piece_size)))
        pieces = []
        for i in xrange(piece_count):
            pieces.append(raw_data[i*piece_size:i*piece_size + piece_size])
        return pieces