from ui_folder import saveItem
from ui_folder.uiDetailPage import uiDetailWindow
from PyQt5 import QtCore, QtWidgets
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
        TimerManager.addRepeatTimer(self.data_center.getCfgValue('client', 'tick_time', 1.0), self.update)
        self.showLingtou = True
        self.checkBox.stateChanged.connect(self.onLingtouChecked)

    def update(self):
        state = self.data_center.getState()
        if state == 1:
            detailList = self.data_center.getDetailDataByKey(self.key)
            
            if detailList[0] != 'no stock': 
                if not self.showLingtou:
                    detailList = [i for i in detailList if i[5] >= 100]
            else: detailList = []
            if len(detailList) == 0: 
                detailList = 'no stock'
            saveItem(detailList, QtWidgets.QTableWidgetItem, self)
        elif state == -1:
            self.close()
        pass
    
    def onLingtouChecked(self):
        self.showLingtou = True if self.checkBox.isChecked() else False
