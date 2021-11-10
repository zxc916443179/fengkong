from PyQt5 import QtWidgets, QtCore
from ui_folder.uiWidget import uiWidgetWindow
from common_server.data_module import DataCenter
from common_server.timer import TimerManager
from ui_folder import saveItem

class MyMainForm(QtWidgets.QMainWindow, uiWidgetWindow):
    switch_Detail = QtCore.pyqtSignal()
    def __init__(self, key, mainList):
        super(MyMainForm, self).__init__()
        self.key = key
        self.data_center = DataCenter()
        self.setupUi(self)
        self.setWindowTitle(key)
        self.tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidget.setRowCount(len(mainList))
        saveItem(mainList, QtWidgets.QTableWidgetItem, self)
        self.pushButton.clicked.connect(self.goDetail)
        TimerManager.addRepeatTimer(1.0, self.update)

    def goDetail(self):
        self.switch_Detail.emit()

    def update(self):
        state = self.data_center.getState()
        if state == 1:
            mainList = self.data_center.getMainDataByKey(self.key)
            self.tableWidget.clearContents()
            saveItem(mainList, QtWidgets.QTableWidgetItem, self)
        pass

