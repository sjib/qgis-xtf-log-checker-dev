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
from qgis.PyQt.QtWidgets import QDockWidget, QListWidgetItem,QSizePolicy,QCheckBox
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

        # make font bold in Qt5 and Qt6 and keep the "_" on windows
        current_font = self.layerName.font()
        current_font.setBold(True)
        self.layerName.setFont(current_font)
        self.layerName.setTextFormat(Qt.TextFormat.PlainText)
        
        self.errorLayer = errorLayer
        QgsProject.instance().layerWillBeRemoved[str].connect(self.layersWillBeRemoved)
        self.checkBox_errors.stateChanged.connect(self.evaluateCheckButtons)
        self.checkBox_warnings.stateChanged.connect(self.evaluateCheckButtons)
        self.checkBox_errors.setEnabled(self.errorLayer != None)
        self.checkBox_errors.setText(QCoreApplication.translate('generals', 'Show errors'))
        self.checkBox_warnings.setText(QCoreApplication.translate('generals', 'Show warnings'))

        # add checkbox for infos
        # dock_panel.ui is shared with the igCheck panel, so the checkbox is
        # inserted from code here instead of being added to the .ui file
        self.checkBox_infos = QCheckBox()
        self.checkBox_infos.setText(QCoreApplication.translate('generals', 'Show infos'))
        # unchecked by default: in ilivalidator logs 'Info' entries are mostly
        # startup noise (java.version, maxMemory, ...) and outnumber real
        # errors by a wide margin
        self.checkBox_infos.setChecked(False)
        self.checkBox_infos.stateChanged.connect(self.evaluateCheckButtons)

        parent_layout = self.verticalLayout
        if parent_layout is not None:
            # insert infos checkbox right after the warnings checkbox
            parent_layout.insertWidget(
                parent_layout.indexOf(self.checkBox_warnings) + 1,
                self.checkBox_infos
            )

        self.listWidget.itemSelectionChanged.connect(self.selectionChanged)
        self.listWidget.itemChanged.connect(self.updateItem)
        self.setWindowTitle(QCoreApplication.translate('generals', 'ilivalidator Error log'))

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
        expressions = []
        if self.checkBox_errors.isChecked():
            expressions.append("\"Type\" = 'Error'")
        if self.checkBox_warnings.isChecked():
            expressions.append("\"Type\" = 'Warning'")
        if self.checkBox_infos.isChecked():
            # 'DetailInfo' is part of the IliVErrors 'Type' enumeration as well
            expressions.append("\"Type\" IN ('Info', 'DetailInfo')")

        expression = " OR ".join(expressions)

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

            # Only flash if the feature has geometry.
            # Features without geometry return a null QgsGeometry, not None,
            # so isNull() is needed here - most 'Info' entries have no coordinate.
            geometry = feature.geometry() if feature is not None else None
            if geometry is not None and not geometry.isNull():
                self.iface.mapCanvas().flashGeometries([geometry])
            # Do NOT call zoomToSelected if there is no geometry

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
