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
from qgis.PyQt.QtWidgets import QDockWidget, QListWidgetItem,QSizePolicy,QCheckBox,QLabel,QComboBox,QHBoxLayout,QPushButton
from qgis.core import QgsVectorLayer, QgsFeatureRequest, QgsProject
from qgis.PyQt.QtCore import QCoreApplication,Qt

# 'Model'/'Topic'/'Class' don't exist as XML elements in the IliVErrors model,
# so they are always empty on the layer. The information is still available,
# encoded in 'ObjTag' as 'Model.Topic.Class' - these are the split positions.
OBJTAG_DERIVED_FIELDS = {'Model': 0, 'Topic': 1, 'Class': 2}


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/dock_panel.ui'))

class XTFLog_DockPanel(QDockWidget, FORM_CLASS):
    EMPTY_VALUE_LABEL = "(empty)"

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

        # add combobox for field/value filter, mirroring the igCheck panel
        self.filterLayout = QHBoxLayout()
        self.filterLayout.setSpacing(4)
        try:
            align_left = Qt.AlignmentFlag.AlignLeft
        except AttributeError:
            align_left = Qt.AlignLeft
        self.filterLayout.setAlignment(align_left)

        self.label_field = QLabel(QCoreApplication.translate('generals', 'Field:'))
        self.label_field.setMaximumWidth(50)
        self.comboBox_field = QComboBox()
        self.comboBox_field.addItems(["All", "Tid", "ObjTag", "Model", "Topic", "Class", "DataSource"])
        self.comboBox_field.setMaximumWidth(100)

        self.label_value = QLabel(QCoreApplication.translate('generals', 'Value:'))
        self.label_value.setMaximumWidth(50)
        self.comboBox_value = QComboBox()
        self.comboBox_value.addItem("All")
        self.comboBox_value.setMinimumWidth(150)

        self.buttonSelectAll = QPushButton(QCoreApplication.translate('generals', 'Select All'))
        self.buttonClearAll = QPushButton(QCoreApplication.translate('generals', 'Clear All'))
        self.buttonSelectAll.clicked.connect(self.SelectAll)
        self.buttonClearAll.clicked.connect(self.ClearAll)

        self.filterLayout.addWidget(self.label_field)
        self.filterLayout.addWidget(self.comboBox_field)
        self.filterLayout.addWidget(self.label_value)
        self.filterLayout.addWidget(self.comboBox_value)
        self.filterLayout.addWidget(self.buttonSelectAll)
        self.filterLayout.addWidget(self.buttonClearAll)

        if parent_layout is not None:
            # insert the filter row right after the infos checkbox
            parent_layout.insertLayout(
                parent_layout.indexOf(self.checkBox_infos) + 1,
                self.filterLayout
            )

        self.comboBox_field.currentIndexChanged.connect(self.updateValueCombo)
        self.comboBox_value.currentIndexChanged.connect(self.updateList)

        # add a label to show the count of displayed errors
        self.countLabel = QLabel()
        self.countLabel.setStyleSheet("color: gray; font-size: 12pt;")
        if parent_layout is not None:
            parent_layout.insertWidget(
                parent_layout.indexOf(self.filterLayout) + 1,
                self.countLabel
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
        if expression:
            expression = f"({expression})"

        # handle field + value filter
        selected_field = self.comboBox_field.currentText()
        selected_value = self.comboBox_value.currentText()

        if selected_field != "All" and selected_value and selected_value != "All":
            escaped_value = selected_value.replace("'", "''")
            if selected_value == self.EMPTY_VALUE_LABEL:
                # Tid/ObjTag/DataSource only exist on 'Error' entries; Model/Topic/Class
                # are derived from ObjTag, so an empty ObjTag means they are empty too
                source_field = 'ObjTag' if selected_field in OBJTAG_DERIVED_FIELDS else selected_field
                field_expr = f"(\"{source_field}\" IS NULL OR \"{source_field}\" = '')"
            elif selected_field in OBJTAG_DERIVED_FIELDS:
                position = OBJTAG_DERIVED_FIELDS[selected_field]
                field_expr = f"array_get(string_to_array(\"ObjTag\", '.'), {position}) = '{escaped_value}'"
            else:
                field_expr = f"\"{selected_field}\" = '{escaped_value}'"

            expression = f"{expression} AND {field_expr}" if expression else field_expr

        if expression:
            self.errorLayer.selectByExpression(expression, QgsVectorLayer.SetSelection)
        else:
            self.errorLayer.removeSelection()

        request = QgsFeatureRequest().setFilterExpression(expression)
        if self.errorLayer:
            for error_feat in self.errorLayer.getFeatures(request):
                listEntry = error_feat.attributes()[TID_idx] + " -- " + error_feat.attributes()[message_idx]
                widgetItem = QListWidgetItem(listEntry, self.listWidget)
                #support for both PyQt5 and PyQt6
                state = Qt.CheckState(error_feat['Checked'])
                widgetItem.setCheckState(state)
        self.isUpdating = False

        # update the displayed item count
        count = self.listWidget.count()
        self.countLabel.setText(QCoreApplication.translate('generals', f'Items: {count}'))

    def updateValueCombo(self):
        if not self.errorLayer:
            return
        self.comboBox_value.clear()
        self.comboBox_value.addItem("All")

        selected_field = self.comboBox_field.currentText()
        if selected_field == "All":
            return

        unique_vals = set()
        has_empty = False

        if selected_field in OBJTAG_DERIVED_FIELDS:
            position = OBJTAG_DERIVED_FIELDS[selected_field]
            objtag_idx = self.errorLayer.fields().indexOf('ObjTag')
            for feat in self.errorLayer.getFeatures():
                objtag = feat.attributes()[objtag_idx]
                parts = objtag.split('.') if objtag else []
                if len(parts) > position and parts[position]:
                    unique_vals.add(parts[position])
                else:
                    has_empty = True
        else:
            field_idx = self.errorLayer.fields().indexOf(selected_field)
            if field_idx == -1:
                return
            for feat in self.errorLayer.getFeatures():
                val = feat.attributes()[field_idx]
                if val:
                    unique_vals.add(str(val))
                else:
                    has_empty = True

        for v in sorted(unique_vals):
            self.comboBox_value.addItem(v)
        if has_empty:
            self.comboBox_value.addItem(self.EMPTY_VALUE_LABEL)

    def evaluateCheckButtons(self):
        self.updateList()

    def SelectAll(self):
        self.listWidget.blockSignals(True)
        self.errorLayer.startEditing()
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            if item:
                try:
                    item.setCheckState(Qt.CheckState.Checked)
                except AttributeError:
                    item.setCheckState(Qt.Checked)
                self.setFeatureCheckState(self.errorLayer, item)
        self.errorLayer.commitChanges()
        self.listWidget.blockSignals(False)

    def ClearAll(self):
        self.listWidget.blockSignals(True)
        self.errorLayer.startEditing()
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            if item:
                try:
                    item.setCheckState(Qt.CheckState.Unchecked)
                except AttributeError:
                    item.setCheckState(Qt.Unchecked)
                self.setFeatureCheckState(self.errorLayer, item)
        self.errorLayer.commitChanges()
        self.listWidget.blockSignals(False)

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
