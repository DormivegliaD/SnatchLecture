# UI窗口
import sys

from PyQt5 import QtWidgets

from window_logic import MainWindow


def main():
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
