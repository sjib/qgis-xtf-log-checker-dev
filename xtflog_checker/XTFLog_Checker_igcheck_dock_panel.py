# -*- coding: utf-8 -*-
"""
/***************************************************************************
 XTFLog_igCheck_DockPanel
 A QGIS dock panel to interact with layers generated from igCheck logs.
 Adapted from XTFLog_DockPanel for ilivalidator logs.
                             -------------------
        begin                : 2025-04-01 # Adjusted date
        copyright            : (C) 2025 by GeoWerkstatt GmbH
        email                : support@geowerkstatt.ch
 ***************************************************************************/

/***************************************************************************
 * *
 * This program is free software; you can redistribute it and/or modify  *
 * it under the terms of the GNU General Public License as published by  *
 * the Free Software Foundation; either version 3 of the License, or     *
 * (at your option) any later version.                                   *
 * *
 ***************************************************************************/
"""

import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDockWidget, QListWidgetItem
from qgis.core import QgsVectorLayer, QgsFeatureRequest, QgsProject
from qgis.PyQt.QtCore import QCoreApplication


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/dock_panel.ui'))

class XTFLog_igCheck_DockPanel(QDockWidget, FORM_CLASS):
    def __init__(self, iface, errorLayer, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setupUi(self)
        self.errorLayer = errorLayer
        QgsProject.instance().layerWillBeRemoved[str].connect(self.layersWillBeRemoved)
        self.checkBox_errors.stateChanged.connect(self.evaluateCheckButtons)
        self.checkBox_warnings.stateChanged.connect(self.evaluateCheckButtons)
        self.checkBox_errors.setEnabled(self.errorLayer != None)
        self.checkBox_errors.setText(QCoreApplication.translate('generals', 'Show errors'))
        self.checkBox_warnings.setText(QCoreApplication.translate('generals', 'Show warnings'))
        self.listWidget.itemSelectionChanged.connect(self.selectionChanged)
        self.listWidget.itemChanged.connect(self.updateItem)
        self.setWindowTitle(QCoreApplication.translate('generals', 'igCheck Error log'))

        if not self.errorLayer:
            return
        self.layerName.setText(self.errorLayer.name())
        self.errorLayerId = self.errorLayer.id()
        self.listWidget.clear()
        self.updateList()

    def updateList(self):
        self.isUpdating = True
        error_idx = self.errorLayer.fields().indexOf('ErrorId')
        message_idx = self.errorLayer.fields().indexOf('Description')
        self.listWidget.clear()
        if self.checkBox_errors.isChecked() and self.checkBox_warnings.isChecked():
            expression = " \"Category\" =  \'error\' OR \"Category\" =  \'Warning\'"
        elif self.checkBox_errors.isChecked():
            expression = "\"Category\" = \'error\'"
        elif self.checkBox_warnings.isChecked():
            expression = "\"Category\" = \'Warning\'"
        else:
            expression = ""

        request = QgsFeatureRequest().setFilterExpression(expression)
        if self.errorLayer:
            for error_feat in self.errorLayer.getFeatures(request):
                listEntry = error_feat.attributes()[error_idx] + " -- " + error_feat.attributes()[message_idx]
                widgetItem = QListWidgetItem(listEntry, self.listWidget)
                widgetItem.setCheckState(error_feat['Checked'])
        self.isUpdating = False

    def evaluateCheckButtons(self):
        self.updateList()

    def selectionChanged(self):
        if not self.listWidget.selectedItems():
            return
        selectedErrorId = self.listWidget.selectedItems()[0].text().split(" -- ")[0]
        expression = " \"ErrorId\" = '{}' ".format(selectedErrorId)
        try:
            self.errorLayer.selectByExpression(expression, QgsVectorLayer.SetSelection)
            self.iface.mapCanvas().zoomToSelected(self.errorLayer)
            request = QgsFeatureRequest().setFilterExpression(expression)
            features = self.errorLayer.getFeatures(request)
            for feature in features:
                self.iface.mapCanvas().flashGeometries([feature.geometry()])
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
        expression = " \"ErrorId\" = '{}' ".format(selectedErrorId)
        request = QgsFeatureRequest().setFilterExpression(expression)
        features = layer.getFeatures()
        field_idx = layer.fields().indexOf('Checked')
        features = layer.getFeatures(request)
        for feat in features:
            layer.changeAttributeValue(feat.id(), field_idx, item.checkState())

    def layersWillBeRemoved(self, layerId):
        if(layerId == self.errorLayerId):
            self.close()