
def saveItem(data, QTableWidgetItem, formWindow):
    for i in range(len(data)):
        for j in range(len(data[i])):
            if data[i][j] != None:
                save=str(data[i][j])
                newItem = QTableWidgetItem(save)
                formWindow.tableWidget.setItem(i,j,newItem)