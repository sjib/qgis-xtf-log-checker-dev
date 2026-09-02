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

# Item role holding the QgsFeature id of the entry a list item was built from.
# Looking a feature up by its TID means a full table scan of the memory layer,
# which is what made 'Select All' take minutes on large logs.
try:
    FEATURE_ID_ROLE = Qt.ItemDataRole.UserRole
except AttributeError:
    FEATURE_ID_ROLE = Qt.UserRole


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
        self.comboBox_field.addItems(["All", "Message", "Tid", "ObjTag", "Model", "Topic", "Class", "DataSource"])
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

        # Entries are single-line, so every item has the same height. Saying so
        # lets the view skip the per-item sizeHint pass it would otherwise redo
        # on every change - without this, ticking 11k checkboxes in 'Select All'
        # spends a second in layout. Set from code because dock_panel.ui is
        # shared with the igCheck panel.
        self.listWidget.setUniformItemSizes(True)

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
        type_idx = self.errorLayer.fields().indexOf('Type')
        objtag_idx = self.errorLayer.fields().indexOf('ObjTag')
        tid_idx = self.errorLayer.fields().indexOf('Tid')
        dataSource_idx = self.errorLayer.fields().indexOf('DataSource')
        line_idx = self.errorLayer.fields().indexOf('Line')
        techDetails_idx = self.errorLayer.fields().indexOf('TechDetails')
        checked_idx = self.errorLayer.fields().indexOf('Checked')

        # Filling the list emits itemChanged three times per entry (text, check
        # state, tooltip) and repaints as it goes - 34k round trips into Python
        # for an 11k entry log, all of them discarded by the isUpdating guard.
        self.listWidget.blockSignals(True)
        self.listWidget.setUpdatesEnabled(False)

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
                # attributes() rebuilds the whole attribute list on every call,
                # so read it once per feature rather than once per field
                attrs = error_feat.attributes()
                listEntry = attrs[TID_idx] + " -- " + attrs[message_idx]
                widgetItem = QListWidgetItem(listEntry, self.listWidget)
                widgetItem.setData(FEATURE_ID_ROLE, error_feat.id())
                #support for both PyQt5 and PyQt6
                state = Qt.CheckState(attrs[checked_idx])
                widgetItem.setCheckState(state)

                # Create the tooltip text. Model/Topic/Class don't exist as
                # attributes in the IliVErrors model, so they are derived from
                # ObjTag here instead of being read directly from the feature.
                tooltip_text = f"<b>TID:</b> {attrs[TID_idx]}<br>"
                if type_idx != -1 and attrs[type_idx]:
                    tooltip_text += f"<b>Type:</b> {attrs[type_idx]}<br>"
                tooltip_text += f"<b>Message:</b> {attrs[message_idx]}<br>"

                objtag = attrs[objtag_idx] if objtag_idx != -1 else ""
                if objtag:
                    parts = objtag.split('.')
                    for field_name, position in OBJTAG_DERIVED_FIELDS.items():
                        if len(parts) > position and parts[position]:
                            tooltip_text += f"<b>{field_name}:</b> {parts[position]}<br>"

                if tid_idx != -1 and attrs[tid_idx]:
                    tooltip_text += f"<b>Tid:</b> {attrs[tid_idx]}<br>"
                if dataSource_idx != -1 and attrs[dataSource_idx]:
                    tooltip_text += f"<b>DataSource:</b> {attrs[dataSource_idx]}<br>"
                if line_idx != -1 and attrs[line_idx]:
                    tooltip_text += f"<b>Line:</b> {attrs[line_idx]}<br>"
                if techDetails_idx != -1 and attrs[techDetails_idx]:
                    tooltip_text += f"<b>TechDetails:</b> {attrs[techDetails_idx]}<br>"

                widgetItem.setToolTip(tooltip_text)

        self.listWidget.setUpdatesEnabled(True)
        self.listWidget.blockSignals(False)
        self.isUpdating = False

        # update the displayed item count
        count = self.listWidget.count()
        self.countLabel.setText(QCoreApplication.translate('generals', f'Items: {count}'))

    def updateValueCombo(self):
        if not self.errorLayer:
            return

        # Refilling the box fires currentIndexChanged twice - once for clear(),
        # once for the first entry - and each one used to rebuild the whole
        # list. Fill it silently instead and rebuild once, at the end.
        self.comboBox_value.blockSignals(True)
        try:
            self.comboBox_value.clear()
            self.comboBox_value.addItems(
                ["All"] + self.uniqueFieldValues(self.comboBox_field.currentText()))
        finally:
            self.comboBox_value.blockSignals(False)
        self.updateList()

    def uniqueFieldValues(self, selected_field):
        """Distinct values of the chosen filter field, sorted, '(empty)' last."""
        if selected_field == "All":
            return []

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
                return []
            for feat in self.errorLayer.getFeatures():
                val = feat.attributes()[field_idx]
                if val:
                    unique_vals.add(str(val))
                else:
                    has_empty = True

        values = sorted(unique_vals)
        if has_empty:
            values.append(self.EMPTY_VALUE_LABEL)
        return values

    def evaluateCheckButtons(self):
        self.updateList()

    def SelectAll(self):
        self.setAllCheckStates(True)

    def ClearAll(self):
        self.setAllCheckStates(False)

    def setAllCheckStates(self, checked):
        """Tick or untick every listed entry and mirror it onto the layer.

        The layer is silenced while the loop runs. QGIS panels that listen to
        attributeValueChanged - the attribute table and the undo/redo view -
        redraw on every single change, which made this take about a minute on an
        11k entry log even though the same loop costs 0.1 s outside QGIS. The
        edit buffer still records everything, so commitChanges() below notifies
        the listeners once, with the whole set of changes.
        """
        #support for both PyQt5 and PyQt6
        try:
            state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        except AttributeError:
            state = Qt.Checked if checked else Qt.Unchecked

        field_idx = self.errorLayer.fields().indexOf('Checked')
        self.listWidget.blockSignals(True)
        self.listWidget.setUpdatesEnabled(False)
        self.errorLayer.startEditing()
        self.errorLayer.blockSignals(True)
        try:
            for i in range(self.listWidget.count()):
                item = self.listWidget.item(i)
                item.setCheckState(state)
                self.errorLayer.changeAttributeValue(
                    item.data(FEATURE_ID_ROLE), field_idx, state)
        finally:
            self.errorLayer.blockSignals(False)
            self.listWidget.setUpdatesEnabled(True)
            self.listWidget.blockSignals(False)
        self.errorLayer.commitChanges()
        self.errorLayer.triggerRepaint()

    def selectionChanged(self):
        if not self.listWidget.selectedItems():
            return
        featureId = self.listWidget.selectedItems()[0].data(FEATURE_ID_ROLE)
        try:
            # Get the feature the item was built from
            request = QgsFeatureRequest().setFilterFid(featureId)
            feature = next(self.errorLayer.getFeatures(request), None)

            # Only zoom/flash if the feature has geometry.
            # Features without geometry return a null QgsGeometry, not None,
            # so isNull() is needed here - most 'Info' entries have no coordinate.
            geometry = feature.geometry() if feature is not None else None
            if geometry is not None and not geometry.isNull():
                # narrow the selection down to the clicked error and move the
                # canvas to it, same behaviour as the igCheck panel
                self.errorLayer.selectByIds([featureId])
                self.iface.mapCanvas().zoomToSelected(self.errorLayer)
                self.iface.mapCanvas().flashGeometries([geometry])
            # Entries without a coordinate leave canvas and selection untouched:
            # unlike igCheck, geometry and geometry-less errors share one layer
            # here, and zoomToSelected() on a null geometry would move the
            # canvas to an empty extent.

        except:
            print("Could not select anything")

    def updateItem(self, item):
        if not self.isUpdating:
            if self.errorLayer:
                self.errorLayer.startEditing()
                self.setFeatureCheckState(self.errorLayer, item)
                self.errorLayer.commitChanges()

    def setFeatureCheckState(self, layer, item):
        field_idx = layer.fields().indexOf('Checked')
        layer.changeAttributeValue(item.data(FEATURE_ID_ROLE), field_idx, item.checkState())

    def layersWillBeRemoved(self, layerId):
        if(layerId == self.errorLayerId):
            self.close()
