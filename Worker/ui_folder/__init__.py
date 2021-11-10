import time
from PyQt5 import QtGui
from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer


def saveItem(data, QTableWidgetItem, formWindow):
    for i in range(len(data)):
        for j in range(len(data[i])):
            if data[i][j] != None:
                save=str(data[i][j])
                newItem = QTableWidgetItem(save)
                formWindow.tableWidget.setItem(i,j,newItem)
                if data[i][j] == '**':
                    formWindow.tableWidget.item(i,j).setBackground(QtGui.QColor(255,255,0))
                    music_play('../resource/audio/warn.wav')
                elif data[i][j] == '***':
                    formWindow.tableWidget.item(i,j).setBackground(QtGui.QColor(255,0,0))
                    music_play('../resource/audio/alert.wav')

def music_play(music_path):
        url = QUrl.fromLocalFile(music_path)
        content = QMediaContent(url)
        player = QMediaPlayer()
        player.setMedia(content)
        # self.player.setVolume(100)
        player.play()
        time.sleep(10)
        player.stop()
