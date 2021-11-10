from PyQt5 import QtGui

def saveItem(data, QTableWidgetItem, formWindow):
    for i in range(len(data)):
        for j in range(len(data[i])):
            if data[i][j] != None:
                save=str(data[i][j])
                newItem = QTableWidgetItem(save)
                formWindow.tableWidget.setItem(i,j,newItem)
                if data[i][j] == '**':
                    formWindow.tableWidget.item(i,j).setBackground(QtGui.QColor(255,255,0))
                elif data[i][j] == '***':
                    formWindow.tableWidget.item(i,j).setBackground(QtGui.QColor(255,0,0))