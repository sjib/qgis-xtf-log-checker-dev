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

import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDockWidget, QListWidgetItem,QSizePolicy
from qgis.core import QgsVectorLayer, QgsFeatureRequest, QgsProject
from qgis.PyQt.QtCore import QCoreApplication,Qt


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/dock_panel.ui'))

class XTFLog_DockPanel(QDockWidget, FORM_CLASS):
    def __init__(self, iface, errorLayer, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setupUi(self)
        #fix the panel too big problem because of long file name
        #self.layerName.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        try:
            size_ignored = QSizePolicy.Policy.Ignored
            size_preferred = QSizePolicy.Policy.Preferred
        except AttributeError:
            size_ignored = QSizePolicy.Ignored
            size_preferred = QSizePolicy.Preferred

        self.layerName.setSizePolicy(size_ignored, size_preferred)
        self.errorLayer = errorLayer
        QgsProject.instance().layerWillBeRemoved[str].connect(self.layersWillBeRemoved)
        self.checkBox_errors.stateChanged.connect(self.evaluateCheckButtons)
        self.checkBox_warnings.stateChanged.connect(self.evaluateCheckButtons)
        self.checkBox_errors.setEnabled(self.errorLayer != None)
        self.checkBox_errors.setText(QCoreApplication.translate('generals', 'Show errors'))
        self.checkBox_warnings.setText(QCoreApplication.translate('generals', 'Show warnings'))
        self.listWidget.itemSelectionChanged.connect(self.selectionChanged)
        self.listWidget.itemChanged.connect(self.updateItem)
        self.setWindowTitle(QCoreApplication.translate('generals', 'Error log'))

        if not self.errorLayer:
            return
        self.layerName.setText(self.errorLayer.name())
        self.errorLayerId = self.errorLayer.id()
        self.listWidget.clear()
        self.updateList()

    def updateList(self):
        self.isUpdating = True
        TID_idx = self.errorLayer.fields().indexOf('TID')
        message_idx = self.errorLayer.fields().indexOf('Message')
        self.listWidget.clear()
        if self.checkBox_errors.isChecked() and self.checkBox_warnings.isChecked():
            expression = " \"Type\" =  \'Error\' OR \"Type\" =  \'Warning\'"
        elif self.checkBox_errors.isChecked():
            expression = "\"Type\" = \'Error\'"
        elif self.checkBox_warnings.isChecked():
            expression = "\"Type\" = \'Warning\'"
        else:
            expression = ""

        request = QgsFeatureRequest().setFilterExpression(expression)
        if self.errorLayer:
            for error_feat in self.errorLayer.getFeatures(request):
                listEntry = error_feat.attributes()[TID_idx] + " -- " + error_feat.attributes()[message_idx]
                widgetItem = QListWidgetItem(listEntry, self.listWidget)
                #support for both PyQt5 and PyQt6
                state = Qt.CheckState(error_feat['Checked'])
                widgetItem.setCheckState(state)
        self.isUpdating = False

    def evaluateCheckButtons(self):
        self.updateList()

    def selectionChanged(self):
        if not self.listWidget.selectedItems():
            return
        selectedErrorId = self.listWidget.selectedItems()[0].text().split(" -- ")[0]
        expression = " \"TID\" = '{}' ".format(selectedErrorId)
        try:
            # Get the feature (only one per TID)
            request = QgsFeatureRequest().setFilterExpression(expression)
            feature = next(self.errorLayer.getFeatures(request), None)

            # Only flash if the feature has geometry
            if feature is not None and feature.geometry() is not None:
                self.iface.mapCanvas().flashGeometries([feature.geometry()])
            # Do NOT call zoomToSelected if geometry is None

        except:
            print("Could not select anything")

    def updateItem(self, item):
        if not self.isUpdating:
            if self.errorLayer:
                self.errorLayer.startEditing()
                self.setFeatureCheckState(self.errorLayer, item)
                self.errorLayer.commitChanges()

    def setFeatureCheckState(self, layer, item):
        selectedErrorId = item.text().split(" -- ")[0]
        expression = " \"TID\" = '{}' ".format(selectedErrorId)
        request = QgsFeatureRequest().setFilterExpression(expression)
        features = layer.getFeatures()
        field_idx = layer.fields().indexOf('Checked')
        features = layer.getFeatures(request)
        for feat in features:
            layer.changeAttributeValue(feat.id(), field_idx, item.checkState())

    def layersWillBeRemoved(self, layerId):
        if(layerId == self.errorLayerId):
            self.close()
