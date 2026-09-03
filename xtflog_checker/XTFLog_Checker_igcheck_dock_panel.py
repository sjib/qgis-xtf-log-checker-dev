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
from qgis.PyQt.QtWidgets import QDockWidget, QListWidgetItem, QCheckBox,QSizePolicy,QPushButton
from qgis.core import QgsVectorLayer, QgsFeatureRequest, QgsProject,QgsWkbTypes
from qgis.PyQt.QtCore import QCoreApplication,Qt
from qgis.PyQt.QtWidgets import QWidget,QComboBox,QHBoxLayout, QLabel,QToolButton, QStyle





# Item role holding the QgsFeature id of the entry a list item was built from.
# Looking a feature up by its TID means a full table scan of the memory layer,
# which is what made 'Select All' take minutes on large logs.
try:
    FEATURE_ID_ROLE = Qt.ItemDataRole.UserRole
except AttributeError:
    FEATURE_ID_ROLE = Qt.UserRole


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/dock_panel.ui'))

class XTFLog_igCheck_DockPanel(QDockWidget, FORM_CLASS):
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
        #self.filterLayout.setAlignment(Qt.AlignLeft)
        try:
            align_left = Qt.AlignmentFlag.AlignLeft
        except AttributeError:
            align_left = Qt.AlignLeft

        self.filterLayout.setAlignment(align_left)

        # label + field combobox 
        self.label_field = QLabel(QCoreApplication.translate('generals', 'Field:'))
        self.label_field.setMaximumWidth(50)
        self.comboBox_field = QComboBox()
        self.comboBox_field.addItems(["All", "Class", "Tid", "Topic","ErrorId","Description"])
        self.comboBox_field.setMaximumWidth(100)  

        # label + value combobox
        self.label_value = QLabel(QCoreApplication.translate('generals', 'Value:'))
        self.label_value.setMaximumWidth(50)
        self.comboBox_value = QComboBox()
        self.comboBox_value.addItem("All")
        self.comboBox_value.setMinimumWidth(150)
        
        # add a 'select all' and 'clear all' button
        self.buttonSelectAll = QPushButton(QCoreApplication.translate('generals', 'Select All'))
        self.buttonClearAll = QPushButton(QCoreApplication.translate('generals', 'Clear All'))
        self.buttonSelectAll.clicked.connect(self.SelectAll)
        self.buttonClearAll.clicked.connect(self.ClearAll)
        
        # add widgets to horizontal layout
        self.filterLayout.addWidget(self.label_field)
        self.filterLayout.addWidget(self.comboBox_field)
        self.filterLayout.addWidget(self.label_value)
        self.filterLayout.addWidget(self.comboBox_value)
        #self.filterLayout.addWidget(self.label_selectAll)
        self.filterLayout.addWidget(self.buttonSelectAll)
        self.filterLayout.addWidget(self.buttonClearAll)

        # insert the horizontal layout below infos checkbox
        parent_layout = self.verticalLayout
        if parent_layout is not None:
            parent_layout.insertLayout(
                parent_layout.indexOf(self.checkBox_infos) + 1,
                self.filterLayout
            )

        # connect signals
        self.comboBox_field.currentIndexChanged.connect(self.updateValueCombo)
        # not connected straight to updateList: picking a value should also jump
        # to the first match, and a slot taking an extra argument would receive
        # the combo's index in it
        self.comboBox_value.currentIndexChanged.connect(self.valueFilterChanged)

        self.errorLayer = errorLayer
        QgsProject.instance().layerWillBeRemoved[str].connect(self.layersWillBeRemoved)
        self.checkBox_errors.stateChanged.connect(self.evaluateCheckButtons)
        self.checkBox_warnings.stateChanged.connect(self.evaluateCheckButtons)
        self.checkBox_errors.setEnabled(self.errorLayer != None)
        self.checkBox_errors.setText(QCoreApplication.translate('generals', 'Show errors'))
        self.checkBox_warnings.setText(QCoreApplication.translate('generals', 'Show warnings'))
        # Entries are single-line, so every item has the same height. Saying so
        # lets the view skip the per-item sizeHint pass it would otherwise redo
        # on every change - without this, ticking thousands of checkboxes in
        # 'Select All' spends seconds in layout.
        self.listWidget.setUniformItemSizes(True)

        self.listWidget.itemSelectionChanged.connect(self.selectionChanged)
        self.listWidget.itemChanged.connect(self.updateItem)

        # Create a custom title bar widget
        titleWidget = QWidget()
        titleLayout = QHBoxLayout(titleWidget)
        titleLayout.setContentsMargins(4, 0, 4, 0)  # reduce margins
        titleLayout.setSpacing(6)


        # Left: keep original window title
        geometry_type = self.errorLayer.geometryType()
        if geometry_type == QgsWkbTypes.PointGeometry:
            default_title = "igCheck - Point Errors"
            default_geom = "Point"
        elif geometry_type == QgsWkbTypes.LineGeometry:
            default_title = "igCheck - Line Errors"
            default_geom = "Line"
        elif geometry_type == QgsWkbTypes.PolygonGeometry:
            default_title = "igCheck - Surface Errors"
            default_geom = "Surface"
        else:
            default_title = "igCheck No Geometry Errors"
            default_geom = "No Geometry"

        self.titleLabel = QLabel(default_title)
        titleLayout.addWidget(self.titleLabel)


        # Right: add geometry selector
        self.comboBox_geometry = QComboBox()
        self.comboBox_geometry.addItems(["Point", "Line", "Surface", "No Geometry"])
        self.comboBox_geometry.setMaximumWidth(150)
        self.comboBox_geometry.setCurrentText(default_geom)
        self.comboBox_geometry.currentIndexChanged.connect(self.switchGeometryLayer)
        titleLayout.addWidget(self.comboBox_geometry)
        titleLayout.addStretch()
        # Apply as dock title bar
        self.setTitleBarWidget(titleWidget)

        # Add a label to show the count of displayed errors
        self.countLabel = QLabel()
        self.countLabel.setStyleSheet("color: gray; font-size: 12pt;")
        parent_layout.insertWidget(
            parent_layout.indexOf(self.filterLayout) + 1,
            self.countLabel
        )
        
        # Initialize
        self.geometryLayers = {}

        # Floating / dock toggle button
        self.floatButton = QToolButton()
        self.floatButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))
        self.floatButton.setStyleSheet("QToolButton { color: black; border: none; }")  # no fade, no border
        self.floatButton.setAutoRaise(False)
        self.floatButton.clicked.connect(lambda: self.setFloating(not self.isFloating()))
        self.floatButton.setFixedSize(16, 16)
        #titleLayout.addWidget(self.floatButton)

        # Close button
        closeButton = QToolButton()
        #closeButton.setIcon(self.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        try:
            sp_close = QStyle.StandardPixmap.SP_TitleBarCloseButton
        except AttributeError:
            sp_close = QStyle.SP_TitleBarCloseButton
        closeButton.setIcon(self.style().standardIcon(sp_close))

        closeButton.clicked.connect(self.close)
        closeButton.setFixedSize(16, 16)
        closeButton.setStyleSheet("QToolButton { border: none }")
        #titleLayout.addWidget(closeButton)

        # Create a small layout for the two buttons
        buttonLayout = QHBoxLayout()
        buttonLayout.setContentsMargins(0,0,0,0)
        buttonLayout.setSpacing(0)  # no spacing between the two buttons
        #buttonLayout.addWidget(self.floatButton)
        buttonLayout.addWidget(closeButton)

        # Add this buttonLayout to the main titleLayout
        titleLayout.addLayout(buttonLayout)


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
        checked_idx = self.errorLayer.fields().indexOf('Checked')

        # Filling the list emits itemChanged three times per entry (text, check
        # state, tooltip) and repaints as it goes - all of them discarded by the
        # isUpdating guard.
        self.listWidget.blockSignals(True)
        self.listWidget.setUpdatesEnabled(False)

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
        #request.addOrderBy('$id')
        if self.errorLayer:
            for error_feat in self.errorLayer.getFeatures(request):
                # attributes() rebuilds the whole attribute list on every call,
                # so read it once per feature rather than once per field
                attrs = error_feat.attributes()
                error_id = attrs[error_id_idx]
                error_message = attrs[message_idx]
                TID_value = attrs[TID_idx]
                listEntry = f"{TID_value} -- {error_message} ({error_id})"
                widgetItem = QListWidgetItem(listEntry, self.listWidget)
                widgetItem.setData(FEATURE_ID_ROLE, error_feat.id())
                #support for both PyQt5 and PyQt6
                state = Qt.CheckState(attrs[checked_idx])
                widgetItem.setCheckState(state)

                # Create the tooltip text
                tooltip_text = f"<b>TID:</b> {TID_value}<br>"
                tooltip_text += f"<b>Module:</b> {attrs[Module_idx]}<br>"
                tooltip_text += f"<b>Error ID:</b> {error_id}<br>"
                tooltip_text += f"<b>Model:</b> {attrs[Model_idx]}<br>"
                tooltip_text += f"<b>Description:</b> {error_message}<br>"
                tooltip_text += f"<b>Topic:</b> {attrs[Topic_idx]}<br>"

                if class_idx != -1 and attrs[class_idx]:
                    tooltip_text += f"<b>Class:</b> {attrs[class_idx]}<br>"
                if tid_idx != -1 and attrs[tid_idx]:
                    tooltip_text += f"<b>Tid:</b> {attrs[tid_idx]}<br>"
                if name_idx != -1 and attrs[name_idx]:
                    tooltip_text += f"<b>Name:</b> {attrs[name_idx]}<br>"
                if value_idx != -1 and attrs[value_idx]:
                    tooltip_text += f"<b>Value:</b> {attrs[value_idx]}<br>"

                widgetItem.setToolTip(tooltip_text)

        self.listWidget.setUpdatesEnabled(True)
        self.listWidget.blockSignals(False)
        self.isUpdating = False

        # Update count label
        count = self.listWidget.count()
        self.countLabel.setText(QCoreApplication.translate('generals', f'Items: {count}'))

    def selectFirstItem(self):
        """Jump to the first entry, which moves the canvas to that error.

        Called after either filter combo changes, so the map follows the filter.
        """
        if self.listWidget.count() > 0:
            self.listWidget.setCurrentRow(0)

    def valueFilterChanged(self):
        self.updateList()
        self.selectFirstItem()

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
        self.selectFirstItem()

    def uniqueFieldValues(self, selected_field):
        """Distinct values of the chosen filter field, sorted."""
        # "All" means no filtering, so the box keeps only its "All" entry
        if selected_field == "All":
            return []
        # check if field exists in layer
        field_idx = self.errorLayer.fields().indexOf(selected_field)
        if field_idx == -1:
            return []
        # collect unique values for the chosen field
        unique_vals = set()
        for feat in self.errorLayer.getFeatures():
            val = feat.attributes()[field_idx]
            if val:
                unique_vals.add(str(val))
        return sorted(unique_vals)



    def evaluateCheckButtons(self):
        self.updateList()

    def selectionChanged(self):
        if not self.listWidget.selectedItems():
            return
        featureId = self.listWidget.selectedItems()[0].data(FEATURE_ID_ROLE)
        try:
            self.errorLayer.selectByIds([featureId])
            self.iface.mapCanvas().zoomToSelected(self.errorLayer)
            request = QgsFeatureRequest().setFilterFid(featureId)
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
        field_idx = layer.fields().indexOf('Checked')
        layer.changeAttributeValue(item.data(FEATURE_ID_ROLE), field_idx, item.checkState())

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








