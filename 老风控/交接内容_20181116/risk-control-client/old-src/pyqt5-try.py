import sys
from PyQt5 import QtWidgets

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()
    button = QtWidgets.QPushButton("Hello World!")
    window.setCentralWidget(button)
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()

