# -*- coding: utf-8 -*-
"""XTFLog_Checker
A QGIS plugin to visualize XTF files of the IliVErrors and igChecker.

Begin: 2021-07-13
Copyright: (C) 2025 by GeoWerkstatt GmbH & Stefan Jürg Burckhardt
Email: support@geowerkstatt.ch

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.
"""

from qgis.PyQt.QtCore import QObject, QEvent
import xml.etree.ElementTree as ET
import pathlib

from .XTFLog_Checker_dialog import XTFLog_CheckerDialog


class DropFileFilter(QObject):
    def __init__(self, parent=None):
        super(DropFileFilter, self).__init__(parent.iface.mainWindow())
        self.parent = parent

    def is_handling_requested(self, file_path):
        if pathlib.Path(file_path).suffix[1:] in ['xtf', 'XTF']:
            self.dlg = XTFLog_CheckerDialog(self.parent.iface, file_path)
            self.dlg.show()

        return False

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Drop:
            if len(event.mimeData().urls()) == 1:
                if self.is_handling_requested(event.mimeData().urls()[0].toLocalFile()):
                    if self.parent.handle_dropped_file(event.mimeData().urls()[0].toLocalFile()):
                        return True

        return False
