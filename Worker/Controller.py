from common_server.data_module import DataCenter
from ui_folder.DetailWindow import DetailWindow
from ui_folder.MainWindow import MyMainForm

class Controller(object):
    def __init__(self):
        self.logger = print
        self.windows = []
        self.details = []
        self.info = {}
        self.data_center = DataCenter()
        pass
    
    def showMainWindows(self):
        while True:
            state = self.data_center.getState()
            if state == 1:
                self.info = self.data_center.getData()
                for i, v in self.info.items():
                    self.show_mainUi(i, v['main'], v['detail'])
                return    
        
    def show_mainUi(self, key, mainList, detailList):
        mainUi = MyMainForm(key, mainList)
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
