import time
from PyQt4.phonon import Phonon
from PyQt4.QtCore import QObject, QIODevice, QByteArray
from time import sleep


class Audio(QObject, object):
    instance = None
    first = True

    def __new__(cls, *args, **kwargs):
        if not cls.instance:
            cls.instance = QObject.__new__(cls, *args, **kwargs)
        else:
            cls.first = False
        return cls.instance

    def __init__(self):
        if self.first:
            QObject.__init__(self)

            self.audio_output = Phonon.AudioOutput(Phonon.MusicCategory, self)
            self.media_object = Phonon.MediaObject(self)
            self.audio_buffer = None

            self.media_object.setTickInterval(1000)
            self.tick = self.media_object.tick
            self.state_changed = self.media_object.stateChanged
            self.finished = self.media_object.finished

            Phonon.createPath(self.media_object, self.audio_output)

    def get_media_object(self):
        return self.media_object

    def get_audio_output(self):
        return self.audio_output

    def set_audio_buffer(self, audio_buffer):
        self.audio_buffer = audio_buffer
        self.media_source = Phonon.MediaSource(audio_buffer)
        self.media_object.setCurrentSource(self.media_source)

    def play(self):
        self.media_object.play()

    def finished(self):
        print 'finished'

    def pause(self):
        self.media_object.pause()

    def stop(self):
        self.media_object.stop()

    def state(self):
        return self.media_object.state()


class AudioBuffer(QIODevice):
    def __init__(self, size):
        QIODevice.__init__(self)
        self.offset = 0
        self.size_ = size
        self.buffer_ = QByteArray(size, "\0")
        self.real_len = 0

    def receive_data(self, data):
        self.writeData(data)

    def set_size(self, size):
        self.size_ = size
        if len(self.buffer_) == 0:
            self.buffer_ = QByteArray(size, "\0")

    # Implementation of methods derived from QIODevice
    def size(self):
        return self.size_

    def bytesAvailable(self):
        avail = self.real_len
        avail -= self.offset
        #avail += super(AudioBuffer, self).bytesAvailable()
        return max(avail, 0)

    def readAll(self):
        return QByteArray(self.buffer_)

    def readData(self, maxlen):
        while self.bytesAvailable() == 0:
            qApp.processEvents()
            time.sleep(0.01)

        number = min(maxlen, len(self.buffer_) - self.offset)
        data = self.buffer_[self.offset:self.offset + number]
        self.offset += number

        return str(data)

    def writeData(self, data):
        self.buffer_.replace(self.real_len, len(data), QByteArray(data))
        self.real_len += len(data)
        self.readyRead.emit()

    def seek(self, pos):
        if pos <= len(self.buffer_):
            self.offset = pos
            QIODevice.seek(self, pos)
            return True
        else:
            return False

    def isSequential(self):
        return False

    def pos(self):
        return self.offset


if __name__ == '__main__':
    import sys
    from PyQt4.QtGui import QApplication, qApp
    from PyQt4.QtCore import QThread

    class BufferFiller(QThread):
        def __init__(self, audio_buffer):
            QThread.__init__(self)
            self.file = open('d:/music/Pendulum_-_Witchcraft.mp3', 'rb')
            self.buffer = audio_buffer

        def run(self):
            content_len = 0
            while content_len <= audio_buffer.size():
                audio_buffer.writeData(self.file.read(16536))
                content_len += 16536
                sleep(0.1)

    app = QApplication(sys.argv)
    audio_buffer = AudioBuffer(0)
    audio = Audio()
    filler = BufferFiller(audio_buffer)
    #file = open('d:/music/Pendulum_-_Witchcraft.mp3', 'rb')
    #audio_buffer.writeData(file.read())
    audio.set_audio_buffer(audio_buffer)
    audio.play()
    sleep(3)
    filler.start()
    audio_buffer.set_size(6478668)
    sys.exit(app.exec_())
