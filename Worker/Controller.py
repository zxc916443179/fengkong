from threading import Thread
from PyQt5 import QtWidgets
from common_server.data_module import DataCenter
from setting.keyType import WORKER_STATE
from ui_folder.DetailWindow import DetailWindow
from ui_folder.MainWindow import MyMainForm

class Controller(object):
    def __init__(self):
        self.logger = print
        self.windows = []
        self.details = []
        self.info = {}
        self.data_center = DataCenter()
        self.data_center.regController(self)
        self.warn_win_th = None
        pass
    
    def showMainWindows(self):
        while True:
            state = self.data_center.getState()
            if state == WORKER_STATE.RUNNING:
                self.info = self.data_center.getData()
                for index, (i, v) in enumerate(self.info.items()):
                    self.show_mainUi(i, v['main'], v['detail'], index=index)
                return    
        
    def show_mainUi(self, key, mainList, detailList, index=0):
        mainUi = MyMainForm(key, mainList, index=index)
        mainUi.switch_Detail.connect(lambda:self.show_detailUi(key, detailList))
        mainUi.show()
        self.windows.append(mainUi)

    def show_detailUi(self, key, datailList):
        detailUi = DetailWindow(key, datailList)
        self.details.append(detailUi)
        return detailUi.show()

    def destroyAllWindows(self):
        for detail in self.details:
            detail.close()
            del detail
        for main in self.windows:
            main.close()
            del main
    
    def showWarnWindow(self):
        self.warn_win_th = WarnWindow()
        self.warn_win_th.start()

    def closeWarnWindow(self):
        if self.warn_win_th:
            self.warn_win_th.stop()

class WarnWindow(Thread):
    def __init__(self):
        super(WarnWindow, self).__init__()
        self.warn_win = QtWidgets.QMessageBox()
        self.warn_win.setStyleSheet('QPushButton{font-weight: bold; background: skyblue; border-radius: 14px;'
        'width: 64px; height: 28px; font-size: 20px; text-align: center;}'
        'QLabel{font-weight: bold; font-size: 20px; color: orange}'
        )
        self.warn_win.setWindowTitle("??????????????????")     # QMessageBox??????

        self.warn_win.setText("?????????????????????????????????????????????!")     #  QMessageBox???????????????

        self.warn_win.setStandardButtons(QtWidgets.QMessageBox.Ok)      # QMessageBox???????????????
    
    def run(self) -> None:
        # self.warn_win.show()
        self.warn_win.exec_()
    
    def stop(self):
        if self.warn_win:
            print("stop th")
            self.warn_win.close()
            self.warn_win = None