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

from qgis.PyQt import QtWidgets
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtCore import QTranslator, QSettings, QLocale, QCoreApplication
import xml.etree.ElementTree as ET
import pathlib

from .XTFLog_Checker_dialog import XTFLog_CheckerDialog
from .DropFileFilter import DropFileFilter
import os.path

class XTFLog_Checker:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.actions = []
        self.menu = 'XTFLog-Checker'
        self.first_start = None
        self.event_filter = DropFileFilter(self)
        self.toolbar = self.iface.addToolBar('XTFLog-Checker')
        self.toolbar.setObjectName('XTFLog-Checker')

    def register_event_filter(self):
        if not self.event_filter:
            self.event_filter = DropFileFilter(self)
        self.iface.mainWindow().installEventFilter(self.event_filter)

    def unregister_event_filter(self):
        if self.event_filter:
            self.iface.mainWindow().removeEventFilter(self.event_filter)
            self.event_filter.deleteLater()

    def initGui(self):
        """Initialize Translation."""
        qgis_locale = QLocale(QSettings().value('locale/userLocale'))
        locale_path = os.path.join(os.path.dirname(__file__), 'i18n')
        self.translator = QTranslator()
        self.translator.load(qgis_locale, 'XTFLog_Checker', '_', locale_path)
        QCoreApplication.installTranslator(self.translator)

        """Add a toolbar icon to the toolbar."""
        icon = QIcon(self.icon_path)
        action = QAction(icon, 'XTFLog-Checker', self.iface.mainWindow())
        action.triggered.connect(self.run)
        action.setEnabled(True)

        self.toolbar.addAction(action)
        self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)

        # Will be set False in run()
        self.first_start = True

        self.register_event_filter()

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu('XTFLog-Checker', action)
            self.iface.removeToolBarIcon(action)

        del self.toolbar
        self.unregister_event_filter()


    def run(self):
        """Run method that performs all the real work"""
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = XTFLog_CheckerDialog(self.iface)

        # Show the dialog
        self.dlg.show()

    
