from time import sleep
from setting.keyType import WORKER_STATE
from ui_folder import saveItem
from ui_folder.uiDetailPage import uiDetailWindow
from PyQt5 import QtCore, QtGui, QtWidgets
from common_server.data_module import DataCenter
from common_server.timer import TimerManager

class DetailWindow(QtWidgets.QMainWindow, uiDetailWindow):
    def __init__(self, key, detailList):
        super(DetailWindow, self).__init__()
        self.key = key
        self.data_center = DataCenter()
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidget.setRowCount(len(detailList))
        saveItem(detailList, QtWidgets.QTableWidgetItem, self)
        # self.timer = None
        # self.timer = TimerManager.addRepeatTimer(self.data_center.getCfgValue('client', 'tick_time', 1.0), self.update)
        self.updateThread = UpdateThread(self)
        self.updateThread.start()
        self.updateThread.update.connect(self.update)
        self.showLingtou = True
        self.checkBox.stateChanged.connect(self.onLingtouChecked)

    def update(self, detailList):
        if detailList[0] == "disconnected":
            self.close()
        if detailList[0] != 'no stock':
            if not self.showLingtou:
                detailList = [i for i in detailList if i[5] >= 100]
        else: detailList = []
        if len(detailList) == 0:
            detailList = 'no stock'
        saveItem(detailList, QtWidgets.QTableWidgetItem, self)
        pass

    def onLingtouChecked(self):
        self.showLingtou = True if self.checkBox.isChecked() else False

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        # if self.timer:
        #     TimerManager.cancel(self.timer)
        if self.updateThread:
            self.updateThread.stop()
        return super(DetailWindow, self).closeEvent(a0)

class UpdateThread(QtCore.QThread):
    update = QtCore.pyqtSignal(list)

    def __init__(self, parent) -> None:
        super().__init__(None)
        self.key = parent.key
        self.data_center = DataCenter()
        self.running = True

    def run(self):
        while self.running:
            state = self.data_center.getState()
            if state == WORKER_STATE.RUNNING:
                detailList = self.data_center.getDetailDataByKey(self.key)
                self.update.emit(detailList)
            elif state == WORKER_STATE.DISCONNECTED:
                self.update.emit(["disconnected"])
            sleep(self.data_center.getCfgValue('client', 'tick_time', 1.0))

    def stop(self):
        self.running = False