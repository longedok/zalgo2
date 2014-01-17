# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'main1.ui'
#
# Created: Mon Sep 26 12:55:39 2011
#      by: PyQt4 UI code generator 4.8.5
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(371, 292)
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.layoutWidget = QtGui.QWidget(MainWindow)
        self.layoutWidget.setGeometry(QtCore.QRect(9, 8, 351, 270))
        self.layoutWidget.setObjectName(_fromUtf8("layoutWidget"))
        self.gridLayout = QtGui.QGridLayout(self.layoutWidget)
        self.gridLayout.setMargin(0)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.searchEdit = QtGui.QLineEdit(self.layoutWidget)
        self.searchEdit.setObjectName(_fromUtf8("searchEdit"))
        self.gridLayout.addWidget(self.searchEdit, 0, 0, 1, 3)
        self.searchBtn = QtGui.QPushButton(self.layoutWidget)
        self.searchBtn.setText(QtGui.QApplication.translate("MainWindow", "Поиск", None, QtGui.QApplication.UnicodeUTF8))
        self.searchBtn.setObjectName(_fromUtf8("searchBtn"))
        self.gridLayout.addWidget(self.searchBtn, 0, 3, 1, 1)
        self.playBtn = QtGui.QPushButton(self.layoutWidget)
        self.playBtn.setText(QtGui.QApplication.translate("MainWindow", "Воспроизвести", None, QtGui.QApplication.UnicodeUTF8))
        self.playBtn.setObjectName(_fromUtf8("playBtn"))
        self.gridLayout.addWidget(self.playBtn, 5, 0, 1, 1)
        self.pauseBtn = QtGui.QPushButton(self.layoutWidget)
        self.pauseBtn.setText(QtGui.QApplication.translate("MainWindow", "Пауза", None, QtGui.QApplication.UnicodeUTF8))
        self.pauseBtn.setObjectName(_fromUtf8("pauseBtn"))
        self.gridLayout.addWidget(self.pauseBtn, 5, 1, 1, 1)
        self.stopBtn = QtGui.QPushButton(self.layoutWidget)
        self.stopBtn.setText(QtGui.QApplication.translate("MainWindow", "Остановить", None, QtGui.QApplication.UnicodeUTF8))
        self.stopBtn.setObjectName(_fromUtf8("stopBtn"))
        self.gridLayout.addWidget(self.stopBtn, 5, 2, 1, 1)
        self.seekSlider = phonon.Phonon.SeekSlider(self.layoutWidget)
        self.seekSlider.setObjectName(_fromUtf8("seekSlider"))
        self.gridLayout.addWidget(self.seekSlider, 2, 0, 1, 3)
        self.volumeSlider = phonon.Phonon.VolumeSlider(self.layoutWidget)
        self.volumeSlider.setObjectName(_fromUtf8("volumeSlider"))
        self.gridLayout.addWidget(self.volumeSlider, 5, 3, 1, 1)
        self.timeLbl = QtGui.QLabel(self.layoutWidget)
        self.timeLbl.setText(QtGui.QApplication.translate("MainWindow", "00:00", None, QtGui.QApplication.UnicodeUTF8))
        self.timeLbl.setAlignment(QtCore.Qt.AlignCenter)
        self.timeLbl.setObjectName(_fromUtf8("timeLbl"))
        self.gridLayout.addWidget(self.timeLbl, 2, 3, 1, 1)
        self.trackListView = QtGui.QListView(self.layoutWidget)
        self.trackListView.setObjectName(_fromUtf8("trackListView"))
        self.gridLayout.addWidget(self.trackListView, 6, 0, 1, 4)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        pass

from PyQt4 import phonon
