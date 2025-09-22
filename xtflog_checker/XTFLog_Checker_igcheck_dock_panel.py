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
from qgis.PyQt.QtWidgets import QDockWidget, QListWidgetItem, QCheckBox,QSizePolicy
from qgis.core import QgsVectorLayer, QgsFeatureRequest, QgsProject,QgsWkbTypes
from qgis.PyQt.QtCore import QCoreApplication


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/dock_panel.ui'))

class XTFLog_igCheck_DockPanel(QDockWidget, FORM_CLASS):
    def __init__(self, iface, errorLayer, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setupUi(self)
        #fix the panel too big problem because of long file name
        self.layerName.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        #add checkboxes for infos
        self.checkBox_infos = QCheckBox()
        self.checkBox_infos.setText(QCoreApplication.translate('generals', 'Show infos'))
        self.checkBox_infos.setChecked(True)
        self.checkBox_infos.stateChanged.connect(self.evaluateCheckButtons)

        self.errorLayer = errorLayer
        QgsProject.instance().layerWillBeRemoved[str].connect(self.layersWillBeRemoved)
        self.checkBox_errors.stateChanged.connect(self.evaluateCheckButtons)
        self.checkBox_warnings.stateChanged.connect(self.evaluateCheckButtons)
        self.checkBox_errors.setEnabled(self.errorLayer != None)
        self.checkBox_errors.setText(QCoreApplication.translate('generals', 'Show errors'))
        self.checkBox_warnings.setText(QCoreApplication.translate('generals', 'Show warnings'))
        parent_layout = self.verticalLayout
        if parent_layout is not None:
            parent_layout.insertWidget(
                parent_layout.indexOf(self.checkBox_warnings) + 1,
                self.checkBox_infos
            )
        self.listWidget.itemSelectionChanged.connect(self.selectionChanged)
        self.listWidget.itemChanged.connect(self.updateItem)
        # change window title based on geometry type
        geometry_type = self.errorLayer.geometryType()
        if geometry_type == QgsWkbTypes.PointGeometry:
            self.setWindowTitle(QCoreApplication.translate('generals', 'igCheck - Point Errors'))
        elif geometry_type == QgsWkbTypes.LineGeometry:
            self.setWindowTitle(QCoreApplication.translate('generals', 'igCheck - Line Errors'))
        elif geometry_type == QgsWkbTypes.PolygonGeometry:
            self.setWindowTitle(QCoreApplication.translate('generals', 'igCheck - Surface Errors'))
        else:
            self.setWindowTitle(QCoreApplication.translate('generals', 'igCheck Error log'))

        if not self.errorLayer:
            return
        self.layerName.setText(self.errorLayer.name())
        self.errorLayerId = self.errorLayer.id()
        self.listWidget.clear()
        self.updateList()


    def updateList(self):
        self.isUpdating = True
        TID_idx = self.errorLayer.fields().indexOf('TID')
        error_id_idx = self.errorLayer.fields().indexOf('ErrorId')
        message_idx = self.errorLayer.fields().indexOf('Description')
        Module_idx = self.errorLayer.fields().indexOf('Module')
        Model_idx = self.errorLayer.fields().indexOf('Model')
        Topic_idx = self.errorLayer.fields().indexOf('Topic')
        class_idx = self.errorLayer.fields().indexOf('Class')
        tid_idx = self.errorLayer.fields().indexOf('Tid')
        value_idx = self.errorLayer.fields().indexOf('Value')
        name_idx = self.errorLayer.fields().indexOf('Name')

        self.listWidget.clear()

        expressions = []
        if self.checkBox_errors.isChecked():
            expressions.append("\"Category\" = 'error'")
        if self.checkBox_warnings.isChecked():
            expressions.append("\"Category\" = 'warning'")
        if self.checkBox_infos.isChecked():
            expressions.append("\"Category\" = 'info'")

        if expressions:
            expression = " OR ".join(expressions)
        else:
            expression = ""

        request = QgsFeatureRequest().setFilterExpression(expression)
        if self.errorLayer:
            for error_feat in self.errorLayer.getFeatures(request):
                # listEntry = error_feat.attributes()[error_idx] + " -- " + error_feat.attributes()[message_idx]
                # widgetItem = QListWidgetItem(listEntry, self.listWidget)
                # widgetItem.setCheckState(error_feat['Checked'])
                error_id = error_feat.attributes()[error_id_idx]
                error_message = error_feat.attributes()[message_idx]
                TID_value = error_feat.attributes()[TID_idx]


                listEntry = f"{TID_value} -- {error_message} ({error_id})"
                widgetItem = QListWidgetItem(listEntry, self.listWidget)
                widgetItem.setCheckState(error_feat['Checked'])

                # Create the tooltip text 
                tooltip_text = f"<b>Module:</b> {error_feat.attributes()[Module_idx]}<br>"
                tooltip_text += f"<b>Error ID:</b> {error_feat.attributes()[error_id_idx]}<br>"
                tooltip_text += f"<b>Model:</b> {error_feat.attributes()[Model_idx]}<br>"
                tooltip_text += f"<b>Description:</b> {error_feat.attributes()[message_idx]}<br>"
                tooltip_text += f"<b>Topic:</b> {error_feat.attributes()[Topic_idx]}<br>"
                
                if class_idx != -1 and error_feat.attributes()[class_idx]:
                    tooltip_text += f"<b>Class:</b> {error_feat.attributes()[class_idx]}<br>"
                if tid_idx != -1 and error_feat.attributes()[tid_idx]:
                    tooltip_text += f"<b>Tid:</b> {error_feat.attributes()[tid_idx]}<br>"
                if name_idx != -1 and error_feat.attributes()[name_idx]:
                    tooltip_text += f"<b>Name:</b> {error_feat.attributes()[name_idx]}<br>"
                if value_idx != -1 and error_feat.attributes()[value_idx]:
                    tooltip_text += f"<b>Value:</b> {error_feat.attributes()[value_idx]}<br>"

                widgetItem.setToolTip(tooltip_text)
        self.isUpdating = False


    def evaluateCheckButtons(self):
        self.updateList()

    def selectionChanged(self):
        if not self.listWidget.selectedItems():
            return
        selectedErrorId = self.listWidget.selectedItems()[0].text().split(" -- ")[0]
        expression = " \"TID\" = '{}' ".format(selectedErrorId)
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