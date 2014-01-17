import logging

from PyQt4.QtGui import QApplication

from ui import MainWindow
from network import NetworkThread
from local_io import FileIndexer
from database import Database


class Application(QApplication):
    SELF_HOST, SELF_PORT = 'localhost', 13333
    SERVER_HOST, SERVER_PORT = 'localhost', 13334
    MUSIC_DIR = 'd:\music'

    def __init__(self, argv):
        QApplication.__init__(self, argv)
        log_level = logging.DEBUG if 1 == 1 else logging.INFO
        logging.basicConfig(level=log_level,format='%(name)s: %(message)s')
        self.logger = logging.getLogger('Application')

        port = self.SELF_PORT
        if len(argv) > 1:
            port = int(argv[1])
        self.network = NetworkThread((self.SELF_HOST, port))
        client = False
        if port != self.SERVER_PORT:
            client = True
            self.network.server.connectPeer((self.SERVER_HOST, self.SERVER_PORT))
        self.file_indexer = FileIndexer(self.MUSIC_DIR)
        self.file_indexer.start()

        if client:
            self.database = Database('client_media_db')
        else:
            self.database = Database()

        self.main_window = MainWindow(self.network)
        self.main_window.show()

        self.network.server.musicFound.connect(self.main_window.tracklist_model.setTrackList)
