import math
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
from itertools import cycle

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.ticker import ScalarFormatter

from PyQt4 import QtGui, QtCore

from util import FixedOrderFormatter

class Linetrace(plt.Line2D):
    """
    Represents a linetrace from the data

    x/y: Arrays containing x and y data
    type: Type of linetrace, 'horizontal' or 'vertical'
    position: The position of the linetrace in x or y direction depending on the type
    """
    def __init__(self, x, y, type, position):
        plt.Line2D.__init__(self, x, y, color='red', linewidth=0.5)

        self.type = type
        self.position = position



class Linecut(QtGui.QDialog):
    def __init__(self, parent=None):
        super(Linecut, self).__init__(parent)

        self.fig, self.ax = plt.subplots()
        self.x, self.y = None, None
        self.linetraces = []
        self.colors = cycle('bgrcmykw')

        self.ax.xaxis.set_major_formatter(FixedOrderFormatter())
        self.ax.yaxis.set_major_formatter(FixedOrderFormatter())

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Linecut")

        self.canvas = FigureCanvasQTAgg(self.fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        grid = QtGui.QGridLayout()

        self.cb_reset_cmap = QtGui.QCheckBox('Reset on plot')
        self.cb_reset_cmap.setCheckState(QtCore.Qt.Checked)
        grid.addWidget(self.cb_reset_cmap, 1, 1)

        self.b_save = QtGui.QPushButton('Data to clipboard', self)
        self.b_save.clicked.connect(self.on_clipboard)
        grid.addWidget(self.b_save, 1, 2)

        self.b_save_dat = QtGui.QPushButton('Save data...', self)
        self.b_save_dat.clicked.connect(self.on_save)
        grid.addWidget(self.b_save_dat, 1, 3)

        self.b_copy = QtGui.QPushButton('Figure to clipboard', self)
        self.b_copy.clicked.connect(self.on_copy_figure)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+C"), self, self.on_copy_figure)
        grid.addWidget(self.b_copy, 1, 4)

        self.cb_incremental = QtGui.QCheckBox('Incremental')
        self.cb_incremental.setCheckState(QtCore.Qt.Unchecked)
        grid.addWidget(self.cb_incremental, 2, 1)

        grid.addWidget(QtGui.QLabel('Offset:'), 2, 2)

        self.le_offset = QtGui.QLineEdit('0', self)
        grid.addWidget(self.le_offset, 2, 3)

        self.b_clear = QtGui.QPushButton('Clear', self)
        self.b_clear.clicked.connect(self.on_clear)
        grid.addWidget(self.b_clear, 2, 4)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.addLayout(grid)
        self.setLayout(layout)

        self.resize(500, 500)
        self.move(720, 100)

    def on_reset(self):
        if self.x != None and self.y != None:
            minx, maxx = np.min(self.x), np.max(self.x)
            miny, maxy = np.min(self.y), np.max(self.y)

            xdiff = (maxx - minx) * .1
            ydiff = (maxy - miny) * .1

            self.ax.axis([minx - xdiff, maxx + xdiff, miny - ydiff, maxy + ydiff])
            self.canvas.draw()

    def on_clipboard(self):
        if self.x == None or self.y == None:
            return

        data = pd.DataFrame(np.column_stack((self.x, self.y)), columns=[self.xlabel, self.ylabel])
        data.to_clipboard(index=False)

    def on_save(self):
        if self.x == None or self.y == None:
            return

        path = os.path.dirname(os.path.realpath(__file__))
        filename = QtGui.QFileDialog.getSaveFileName(self, 'Save file', path, '.dat')

        if filename != '':
            data = pd.DataFrame(np.column_stack((self.x, self.y)), columns=[self.xlabel, self.ylabel])
            data.to_csv(filename, sep='\t', index=False)

    def on_copy_figure(self):
        path = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(path, 'test.png')
        self.fig.savefig(path, bbox_inches='tight')

        img = QtGui.QImage(path)
        QtGui.QApplication.clipboard().setImage(img)

    def on_clear(self):
        for line in self.linetraces:
            line.remove()

        self.linetraces = []

        self.fig.canvas.draw()
    
    def plot_linetrace(self, x, y, type, position, title, xlabel, ylabel):
        # Don't draw lines consisting of one point
        if np.count_nonzero(~np.isnan(y)) < 2:
            return

        self.xlabel, self.ylabel = xlabel, ylabel
        self.x, self.y = x, y

        self.ax.set_title(title)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)

        # Remove all the existing lines and only plot one if we uncheck the incremental box
        # Else, add a new line to the collection
        if self.cb_incremental.checkState() == QtCore.Qt.Unchecked:
            for line in self.linetraces:
                line.remove()
                
            self.linetraces = []

            line = Linetrace(x, y, type, position)
            self.linetraces.append(line)
            self.ax.add_line(line)

            self.total_offset = 0
        else:
            if len(self.ax.lines) > 0:
                if self.ax.lines[-1].position == position:
                    return

            index = len(self.linetraces) - 1

            offset = float(self.le_offset.text())
            line = Linetrace(x, y + index * offset, type, position)
            line.set_color(self.colors.next())

            self.linetraces.append(line)
            self.ax.add_line(line)

        if self.cb_reset_cmap.checkState() == QtCore.Qt.Checked:
            x, y = np.ma.masked_invalid(x), np.ma.masked_invalid(y)
            minx, maxx = np.min(x), np.max(x)
            miny, maxy = np.min(y), np.max(y)

            xdiff = (maxx - minx) * .05
            ydiff = (maxy - miny) * .05

            self.ax.axis([minx - xdiff, maxx + xdiff, miny - ydiff, maxy + ydiff])

        self.ax.set_aspect('auto')
        self.fig.tight_layout()

        self.fig.canvas.draw()

    def resizeEvent(self, event):
        self.fig.tight_layout()
        self.canvas.draw()

    def show_window(self):
        self.show()
        self.raise_()

    def closeEvent(self, event):
        self.hide()
        event.ignore()