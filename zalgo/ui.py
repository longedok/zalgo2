#encoding: utf8
import sys
import logging

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import QVariant, Qt, pyqtSignal
from PyQt4.phonon import Phonon

from main_window_auto import Ui_MainWindow
from audio import Audio

class MainWindow(QtGui.QMainWindow):
    def __init__(self, network, parent=None):
        super(MainWindow, self).__init__()

        self.logger = logging.getLogger('MainWindow')

        self.tracklist_model = TracklistModel()
        if network:
            self.network = network.server

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.trackListView.setModel(self.tracklist_model)
        self.ui.trackListView.doubleClicked.connect(self.listDoubleClicked)
        self.ui.trackListView.clicked.connect(self.listClicked)
        self.ui.searchBtn.clicked.connect(self.searchBtnClick)
        self.ui.playBtn.clicked.connect(self.playBtnClick)
        self.ui.stopBtn.clicked.connect(self.stopBtnClick)
        self.ui.pauseBtn.clicked.connect(self.pauseBtnClick)
        self.setWindowTitle(u'Сетевой Проигрыватель')

        self.current_stream_id = None
        self.current_track = None
        self.audio = Audio()
        self.audio.tick.connect(self.tick)
        self.audio.state_changed.connect(self.stateChanged)
        self.audio.finished.connect(self.playingFinished)
        self.ui.seekSlider.setMediaObject(self.audio.get_media_object())
        self.ui.volumeSlider.setAudioOutput(self.audio.get_audio_output())

        self.ui.pauseBtn.setEnabled(False)
        self.ui.playBtn.setEnabled(True)
        self.ui.stopBtn.setEnabled(False)

    def stateChanged(self, newState, oldState):
        self.ui.pauseBtn.setEnabled(False)
        self.ui.playBtn.setEnabled(False)
        self.ui.stopBtn.setEnabled(False)
        
        if newState == Phonon.PlayingState:
            self.ui.pauseBtn.setEnabled(True)
            self.ui.stopBtn.setEnabled(True)
        elif newState == Phonon.StoppedState:
            self.ui.playBtn.setEnabled(True)
            self.ui.timeLbl.setText("00:00")
        elif newState == Phonon.PausedState:
            self.ui.playBtn.setEnabled(True)
            self.ui.stopBtn.setEnabled(True)

    def tick(self, time):
        displayTime = QtCore.QTime(0, (time / 60000) % 60, (time / 1000) % 60)
        self.ui.timeLbl.setText(displayTime.toString('mm:ss'))

    def playingFinished(self):
        current_index = self.ui.trackListView.currentIndex()
        peers, hash = self.tracklist_model.data(current_index, Qt.UserRole)
        if self.current_track != hash:
            pass

    def searchBtnClick(self):
        search_text = self.ui.searchEdit.text()
        if len(search_text) > 0:
            self.tracklist_model.reset()
            self.current_index = None
            self.tracklist_model.request_id = self.network.search(search_text+"%")

    def playBtnClick(self):
        current_index = self.ui.trackListView.currentIndex()
        peers, hash = self.tracklist_model.data(current_index, Qt.UserRole)
        if self.current_track != hash:
            self.current_track = hash
            self.logger.debug("query to stream track [hash: %s]" % hash)
            self.current_stream_id = self.network.initiateFileStream(peers, hash)
            if self.current_stream_id:
                stream_handler = self.network.getStreamHandlerById(self.current_stream_id)
                self.audio.set_audio_buffer(stream_handler.get_audio_buffer())
                self.audio.play()
        else:
            if self.audio.state() == Phonon.PausedState:
                self.audio.play()
            else:
                self.stopBtnClick()
                self.audio.play()


    def stopBtnClick(self):
        if self.current_stream_id:
            self.network.getStreamHandlerById(self.current_stream_id).stop()
        self.audio.stop()

    def pauseBtnClick(self):
        self.audio.pause()

    def listDoubleClicked(self, item):
        current_index = self.ui.trackListView.currentIndex()
        peers, hash = self.tracklist_model.data(current_index, Qt.UserRole)
        if self.current_track != hash:
            self._mediaObject.stop()
        self.playBtnClick()

    def listClicked(self, item):
        self.ui.playBtn.setEnabled(True)

class TracklistModel(QtCore.QAbstractListModel):
    tracklist = []
    request_id = u""
    hash_to_peers = {}

    def __init__(self, parent=None):
        super(TracklistModel, self).__init__() 

    # Slots
    def setTrackList(self, request_id, tracks, peer):
        if self.request_id == request_id:
            len_before_append = len(self.tracklist)
            first = len_before_append - 1 if len_before_append > 0 else 0
            self.tracklist += tracks
            second = len(self.tracklist)
            self.rowsInserted.emit(None, first, second)
            for tr in tracks:
                if self.hash_to_peers.has_key(tr['hash']):
                    self.hash_to_peers[tr['hash']].append(peer)
                else:
                    self.hash_to_peers[tr['hash']] = [peer]

    # QAbstractModel methods
    def reset(self):
        self.tracklist = []

    def rowCount(self, index):
        return len(self.tracklist)

    def data(self, index, role=Qt.DisplayRole):
        tr = self.tracklist[index.row()]
        if role == Qt.DisplayRole:   
            return QVariant("%s - %s (%s)" % (tr['artist'], tr['title'], tr['album']))
        elif role == Qt.UserRole:
            return (self.hash_to_peers[tr['hash']], tr['hash'])

if __name__ == '__main__':
    import sys
    from PyQt4.QtGui import QApplication
    app = QApplication(sys.argv)

    app2 = MainWindow(None)
    app2.initAudio()
    sys.exit(app.exec_())
