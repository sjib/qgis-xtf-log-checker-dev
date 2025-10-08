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
from qgis.core import QgsVectorLayer, QgsFeatureRequest, QgsProject
from qgis.PyQt.QtCore import QCoreApplication
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QHBoxLayout, QLabel
from PyQt5.QtCore import Qt
from qgis.PyQt.QtWidgets import QWidget
from PyQt5.QtWidgets import QToolButton, QStyle




FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/dock_panel.ui'))

class XTFLog_igCheck_DockPanel(QDockWidget, FORM_CLASS):
    def __init__(self, iface, errorLayer, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setupUi(self)

        #fix the panel too big problem because of long file name
        self.layerName.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

        # add checkbox for infos
        self.checkBox_infos = QCheckBox()
        self.checkBox_infos.setText(QCoreApplication.translate('generals', 'Show infos'))
        self.checkBox_infos.setChecked(True)
        self.checkBox_infos.stateChanged.connect(self.evaluateCheckButtons)

        parent_layout = self.verticalLayout
        if parent_layout is not None:
            # insert infos checkbox right after the warnings checkbox
            parent_layout.insertWidget(
                parent_layout.indexOf(self.checkBox_warnings) + 1,
                self.checkBox_infos
            )

        # add combobox for class filter,horizontal layout for advanced filters
        self.filterLayout = QHBoxLayout()
        self.filterLayout.setSpacing(4)
        self.filterLayout.setAlignment(Qt.AlignLeft)

        # label + field combobox
        self.label_field = QLabel("Field:")
        self.label_field.setMaximumWidth(50)
        self.comboBox_field = QComboBox()
        self.comboBox_field.addItems(["All", "Class", "Tid", "Topic","ErrorId","Description"])
        self.comboBox_field.setMaximumWidth(100)  

        # label + value combobox
        self.label_value = QLabel("Value:")
        self.label_value.setMaximumWidth(50)
        self.comboBox_value = QComboBox()
        self.comboBox_value.addItem("All")
        self.comboBox_value.setMinimumWidth(150)

        # add widgets to horizontal layout
        self.filterLayout.addWidget(self.label_field)
        self.filterLayout.addWidget(self.comboBox_field)
        self.filterLayout.addWidget(self.label_value)
        self.filterLayout.addWidget(self.comboBox_value)

        # insert the horizontal layout below infos checkbox
        parent_layout = self.verticalLayout
        if parent_layout is not None:
            parent_layout.insertLayout(
                parent_layout.indexOf(self.checkBox_infos) + 1,
                self.filterLayout
            )

        # connect signals
        self.comboBox_field.currentIndexChanged.connect(self.updateValueCombo)
        self.comboBox_value.currentIndexChanged.connect(self.updateList)

        self.errorLayer = errorLayer
        QgsProject.instance().layerWillBeRemoved[str].connect(self.layersWillBeRemoved)
        self.checkBox_errors.stateChanged.connect(self.evaluateCheckButtons)
        self.checkBox_warnings.stateChanged.connect(self.evaluateCheckButtons)
        self.checkBox_errors.setEnabled(self.errorLayer != None)
        self.checkBox_errors.setText(QCoreApplication.translate('generals', 'Show errors'))
        self.checkBox_warnings.setText(QCoreApplication.translate('generals', 'Show warnings'))
        self.listWidget.itemSelectionChanged.connect(self.selectionChanged)
        self.listWidget.itemChanged.connect(self.updateItem)

        # Create a custom title bar widget
        titleWidget = QWidget()
        titleLayout = QHBoxLayout(titleWidget)
        titleLayout.setContentsMargins(4, 0, 4, 0)  # reduce margins
        titleLayout.setSpacing(6)

        # Left: keep original window title
        self.titleLabel = QLabel("igCheck - Point Errors")  # default title
        titleLayout.addWidget(self.titleLabel)

        # Right: add geometry selector
        self.comboBox_geometry = QComboBox()
        self.comboBox_geometry.addItems(["Point", "Line", "Surface", "No Geometry"])
        self.comboBox_geometry.setMaximumWidth(150)
        self.comboBox_geometry.currentIndexChanged.connect(self.switchGeometryLayer)
        titleLayout.addWidget(self.comboBox_geometry)
        titleLayout.addStretch()
        # Apply as dock title bar
        self.setTitleBarWidget(titleWidget)
        
        # Initialize
        self.geometryLayers = {}

        # Close button
        closeButton = QToolButton()
        closeButton.setIcon(self.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        closeButton.clicked.connect(self.close)
        titleLayout.addWidget(closeButton)


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

        # combine category filters
        if expressions:
            expression = " OR ".join(expressions)
        else:
            expression = ""

        # handle field + value filter
        selected_field = self.comboBox_field.currentText()
        selected_value = self.comboBox_value.currentText()

        if selected_field != "All" and selected_value and selected_value != "All":
            field_idx = self.errorLayer.fields().indexOf(selected_field)
            if field_idx != -1:
                field_expr = f"\"{selected_field}\" = '{selected_value}'"
                if expression:
                    expression = f"({expression}) AND {field_expr}"
                else:
                    expression = field_expr

        # now apply expression to layer
        if expression:
            self.errorLayer.selectByExpression(expression, QgsVectorLayer.SetSelection)
        else:
            self.errorLayer.removeSelection()

        request = QgsFeatureRequest().setFilterExpression(expression)
        if self.errorLayer:
            for error_feat in self.errorLayer.getFeatures(request):
                error_id = error_feat.attributes()[error_id_idx]
                error_message = error_feat.attributes()[message_idx]
                TID_value = error_feat.attributes()[TID_idx]
                listEntry = f"{TID_value} -- {error_message} ({error_id})"
                widgetItem = QListWidgetItem(listEntry, self.listWidget)
                widgetItem.setCheckState(error_feat['Checked'])

                # Create the tooltip text
                tooltip_text = f"<b>TID:</b> {error_feat.attributes()[TID_idx]}<br>" 
                tooltip_text += f"<b>Module:</b> {error_feat.attributes()[Module_idx]}<br>"
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

        sender = self.sender()
        #if isinstance(sender, QComboBox):  # only when combobox triggered
        #    if self.listWidget.count() > 0:
        #        self.listWidget.setCurrentRow(0)
        if sender is self.comboBox_value:
            if self.listWidget.count() > 0:
                self.listWidget.setCurrentRow(0)


    def updateValueCombo(self):
        if not self.errorLayer:
            return
        # clear old values
        self.comboBox_value.clear()
        self.comboBox_value.addItem("All")  # default option
        # get selected field
        selected_field = self.comboBox_field.currentText()
        # "All" means no filtering, so keep only "All"
        if selected_field == "All":
            return
        # check if field exists in layer
        field_idx = self.errorLayer.fields().indexOf(selected_field)
        if field_idx == -1:
            return
        # collect unique values for the chosen field
        unique_vals = set()
        for feat in self.errorLayer.getFeatures():
            val = feat.attributes()[field_idx]
            if val:
                unique_vals.add(str(val))
        # add them to value combobox
        for v in sorted(unique_vals):
            self.comboBox_value.addItem(v)



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


    def switchGeometryLayer(self, index):
        """Switch between Point / Line / Surface / No Geometry layers."""
        if not hasattr(self, 'iface') or not self.iface:
            return

        selected_type = self.comboBox_geometry.currentText()
        print(f"🔄 Switching to geometry type: {selected_type}")

        # Define layer name keywords to search for
        keyword_map = {
            "Point": "_igChecker_Points",
            "Line": "_igChecker_Lines",
            "Surface": "_igChecker_Surfaces",
            "No Geometry": "_igChecker_NoGeometry"
        }

        keyword = keyword_map.get(selected_type)
        if not keyword:
            print(f"⚠️ Unknown geometry type: {selected_type}")
            return

        # Search for the layer containing the keyword
        target_layer = None
        for layer in QgsProject.instance().mapLayers().values():
            if keyword in layer.name():
                target_layer = layer
                break

        if not target_layer:
            print(f"⚠️ Layer not found for keyword: {keyword}")
            return

        # Update error layer
        self.errorLayer = target_layer
        self.layerName.setText(target_layer.name())

        # Update title label
        self.titleLabel.setText(f"igCheck - {selected_type} Errors")


        # Reset filter combos when switching layer
        self.comboBox_field.blockSignals(True)
        self.comboBox_value.blockSignals(True)
        self.comboBox_field.setCurrentIndex(0)  # "All"
        self.comboBox_value.clear()
        self.comboBox_value.addItem("All")
        self.comboBox_field.blockSignals(False)
        self.comboBox_value.blockSignals(False)

        # Refresh list contents
        self.updateList()

        # Zoom to the full extent of the new layer
        if target_layer:
            self.iface.mapCanvas().setExtent(target_layer.extent())
            self.iface.mapCanvas().refresh()

        print(f"✅ Switched to layer: {target_layer.name()}")



