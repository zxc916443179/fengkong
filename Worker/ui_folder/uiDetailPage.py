# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'detail.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtWidgets


class uiDetailWindow(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(800, 600)
        self.centralwidget = QtWidgets.QWidget(Form)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setContentsMargins(3, 3, 3, 3)
        self.verticalLayout.setObjectName("verticalLayout")
        self.checkBox = QtWidgets.QCheckBox(self.centralwidget)
        # self.checkBox.setGeometry(QtCore.QRect(0, 690, 631, 41))
        self.checkBox.setObjectName("checkBoxButton")
        self.checkBox.setText("零头股")
        self.checkBox.setChecked(True)
        self.tableWidget = QtWidgets.QTableWidget(self.centralwidget)
        # self.tableWidget.setGeometry(QtCore.QRect(0, 0, 1051, 681))
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(9)
        self.tableWidget.setRowCount(0)
        self.tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableWidget.horizontalHeader().setStyleSheet("QHeaderView::section{background:skyblue;color: black;}")
        self.tableWidget.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.verticalLayout.addWidget(self.tableWidget)
        self.verticalLayout.addWidget(self.checkBox)
        Form.setCentralWidget(self.centralwidget)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(4, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(5, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(6, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(7, item)
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(8, item)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Detail"))
        item = self.tableWidget.horizontalHeaderItem(0)
        item.setText(_translate("Form", "操作"))
        item = self.tableWidget.horizontalHeaderItem(1)
        item.setText(_translate("Form", "交易员"))
        item = self.tableWidget.horizontalHeaderItem(2)
        item.setText(_translate("Form", "证券代码"))
        item = self.tableWidget.horizontalHeaderItem(3)
        item.setText(_translate("Form", "证券名称"))
        item = self.tableWidget.horizontalHeaderItem(4)
        item.setText(_translate("Form", "浮动盈亏"))
        item = self.tableWidget.horizontalHeaderItem(5)
        item.setText(_translate("Form", "仓位"))
        item = self.tableWidget.horizontalHeaderItem(6)
        item.setText(_translate("Form", "收益率"))
        item = self.tableWidget.horizontalHeaderItem(7)
        item.setText(_translate("Form", "状态"))
        item = self.tableWidget.horizontalHeaderItem(8)
        item.setText(_translate("Form", "持仓市值"))

