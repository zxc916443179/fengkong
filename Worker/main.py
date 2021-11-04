import sys

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QColor, QBrush
from ui_folder.uiWidget import uiWidgetWindow
from ui_folder.uiDetailPage import uiDetailWindow

class Controller:
    def __init__(self):
        pass
   
    def show_mainUi(self):
        self.mainUi = MyMainForm()
        self.mainUi.switch_Detail.connect(self.show_detailUi)
        self.mainUi.show()
   
    def show_detailUi(self):
        self.detailUi = DetailWindow()
        self.detailUi.show()
   

class MyMainForm(QtWidgets.QMainWindow, uiWidgetWindow):
    switch_Detail = QtCore.pyqtSignal()
    def __init__(self, parent=None):
        super(MyMainForm, self).__init__(parent)
        self.setupUi(self)
        self.pushButton.clicked.connect(self.goDetail)
    def goDetail(self):
        self.switch_Detail.emit()

class DetailWindow(QtWidgets.QMainWindow, uiDetailWindow):
    def __init__(self):
        super(DetailWindow, self).__init__()
        self.setupUi(self)

def main():
    app = QtWidgets.QApplication(sys.argv)
    controller = Controller() 
    controller.show_mainUi() 
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()