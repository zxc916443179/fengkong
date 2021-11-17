
from PyQt5 import QtGui
from .MediaPlayer import MediaPlayer


def saveItem(data, QTableWidgetItem, formWindow):
    from ui_folder.MainWindow import MyMainForm
    warnLevel = 0
    if data == 'no stock': 
        formWindow.tableWidget.setItem(0, 0, QTableWidgetItem(str(data)))
    else: 
        for i in range(len(data)):
            for j in range(len(data[i])):
                if data[i][j] != None:
                    save=str(data[i][j])
                    newItem = QTableWidgetItem(save)
                    formWindow.tableWidget.setItem(i, j, newItem)
                    if data[i][j] == '**':
                        formWindow.tableWidget.item(i, j).setBackground(QtGui.QColor(255, 255, 0))
                        warnLevel = 1
                    elif data[i][j] == '***':
                        formWindow.tableWidget.item(i, j).setBackground(QtGui.QColor(255, 0, 0))
                        warnLevel = 2
    
    if type(formWindow) is MyMainForm:
        musicPath = './resource/audio/warn.wav' if warnLevel == 1 else './resource/audio/alert.wav'
        formWindow.showWarnWindow(warnLevel=warnLevel, musicPath=musicPath)

def musicPlay(musicPath):
    MediaPlayer(musicPath).start()
