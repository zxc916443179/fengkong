from PyQt5 import QtGui, QtWidgets, QtCore
from common.message_queue_module import Message, MsgQueue
from setting.keyType import WORKER_STATE
from ui_folder.uiWidget import uiWidgetWindow
from common_server.data_module import DataCenter
from common_server.timer import TimerManager
from ui_folder import saveItem, musicPlay

class MyMainForm(QtWidgets.QMainWindow, uiWidgetWindow):
    switch_Detail = QtCore.pyqtSignal()
    warn_signal = QtCore.pyqtSignal()
    def __init__(self, key, mainList, index=0):
        super(MyMainForm, self).__init__()
        self.key = key
        self.data_center = DataCenter()
        self.data_center.registerWarnChangedEvent(self.onWarnChanged)
        self.isWarned = False
        self.setupUi(self, index)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle(key)
        self.msgQueue = MsgQueue()
        self.tableWidget.setRowCount(len(mainList))
        # saveItem(mainList, QtWidgets.QTableWidgetItem, self)
        self.pushButton.clicked.connect(self.goDetail)
        self.warn_signal.connect(lambda:self.onEmitWarnWindow())
        self.warnLevel = 0
        self.musicPath = None
        self.timer = None
        self.timer = TimerManager.addRepeatTimer(self.data_center.getCfgValue('client', 'tick_time', 1.0), self.update)
        self.checkBox.stateChanged.connect(self.onWarningChecked)

    def onWarnChanged(self, ifWarnNeed):
        self.checkBox.setChecked(ifWarnNeed)

    def onEmitWarnWindow(self):
        if self.musicPath is not None:
            musicPlay(self.musicPath)
        QtWidgets.QMessageBox.about(self, self.key, "警告" if self.warnLevel == 1 else "报警")
        pass

    def goDetail(self):
        self.switch_Detail.emit()

    def update(self):
        state = self.data_center.getState()
        if state == WORKER_STATE.RUNNING:
            mainList = self.data_center.getMainDataByKey(self.key)
            saveItem(mainList, QtWidgets.QTableWidgetItem, self)
        elif state == WORKER_STATE.DISCONNECTED:
            self.close()
        pass
    
    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        reply = QtWidgets.QMessageBox.question(self,
                                               '本程序',
                                               "是否要退出程序？",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                               QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            if self.timer:
                TimerManager.cancel(self.timer)
            import os
            print("exit")
            os._exit(0)
        else:
            event.ignore()
    
    def showWarnWindow(self, warnLevel: int, musicPath = None) -> None:
        ifWarnNeed = self.data_center.getIfWarn()
        if warnLevel == 0 or ifWarnNeed:
            self.isWarned = False
            self.musicPath = None
            return
        if not self.isWarned:
            self.isWarned = True
            self.warnLevel = warnLevel
            if musicPath:
                self.musicPath = musicPath
            self.warn_signal.emit()

    def onWarningChecked(self):
        self.data_center.setIfWarn(True if self.checkBox.isChecked() else False)
        