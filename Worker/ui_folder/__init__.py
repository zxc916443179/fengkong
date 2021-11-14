import time
from PyQt5 import QtGui
from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer



def saveItem(data, QTableWidgetItem, formWindow):
    from ui_folder.MainWindow import MyMainForm
    warnLevel = 0
    for i in range(len(data)):
        for j in range(len(data[i])):
            if data[i][j] != None:
                save=str(data[i][j])
                newItem = QTableWidgetItem(save)
                formWindow.tableWidget.setItem(i, j, newItem)
                if data[i][j] == ' ':
                    formWindow.tableWidget.item(i, j).setBackground(QtGui.QColor(255, 255, 0))
                    warnLevel = 1
                elif data[i][j] == '***':
                    formWindow.tableWidget.item(i, j).setBackground(QtGui.QColor(255, 0, 0))
                    warnLevel = 2
    if type(formWindow) is MyMainForm:
        musicPath = '../resource/audio/warn.wav' if warnLevel == 1 else '../resource/audio/alert.wav'
        formWindow.showWarnWindow(warnLevel=warnLevel, musicPath=musicPath)

def musicPlay(music_path):
        url = QUrl.fromLocalFile(music_path)
        content = QMediaContent(url)
        player = QMediaPlayer()
        player.setMedia(content)
        # self.player.setVolume(100)
        player.play()
