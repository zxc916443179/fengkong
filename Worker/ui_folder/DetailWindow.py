from ui_folder import saveItem
from ui_folder.uiDetailPage import uiDetailWindow
from PyQt5 import QtWidgets
from common_server.data_module import DataCenter
from common_server.timer import TimerManager

class DetailWindow(QtWidgets.QMainWindow, uiDetailWindow):
    def __init__(self, key, detailList):
        super(DetailWindow, self).__init__()
        self.key = key
        self.data_center = DataCenter()
        self.setupUi(self)
        self.tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidget.setRowCount(len(detailList))
        saveItem(detailList, QtWidgets.QTableWidgetItem, self)
        TimerManager.addRepeatTimer(1.0, self.update)
        self.showLingtou = False
        self.checkBox.stateChanged.connect(self.onLingtouChecked)

    def update(self):
        state = self.data_center.getState()
        if state == 1:
            detailList = self.data_center.getDetailDataByKey(self.key)
            self.tableWidget.clearContents()
            if not self.showLingtou:
                detailList = [i for i in detailList if i[5] >= 100]
            saveItem(detailList, QtWidgets.QTableWidgetItem, self)
        elif state == -1:
            self.close()
        pass
    
    def onLingtouChecked(self):
        self.showLingtou = True if self.checkBox.isChecked() else False
