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
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import Qt, QMetaType,QCoreApplication
from qgis.core import QgsVectorLayer, QgsField, QgsProject, QgsFeature, QgsGeometry, QgsPointXY, QgsEditorWidgetSetup, QgsMapLayerType,QgsMessageLog
# 3.7.2025
from qgis.core import Qgis
import requests
import re
import xml.etree.ElementTree as ET
from .XTFLog_Checker_dock_panel import XTFLog_DockPanel
from .XTFLog_Checker_igcheck_dock_panel import XTFLog_igCheck_DockPanel

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/dialog_base.ui'))

class XTFLog_CheckerDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, file_path=None, parent=None):
        """Constructor."""
        super(XTFLog_CheckerDialog, self).__init__(parent)
        self.setupUi(self)
        self.btn_input.clicked.connect(self.getInputFile)
        self.btn_run.clicked.connect(self.visualizeLog)
        self.btn_run.setText(QCoreApplication.translate('generals', 'Create layer'))
        self.btn_run.setEnabled(file_path != None)
        self.btn_cancel.clicked.connect(self.closePlugin)
        self.btn_cancel.setText(QCoreApplication.translate('generals', 'Cancel'))
        self.attributeNames = ["Type", "Message","Description","Category", "Tid", "ObjTag","Model", "TechId","Topic", "UserId","Class","Name","Value", "IliQName", "DataSource", "Line", "TechDetails"]
        self.btn_show_error_log.clicked.connect(self.showErrorLog)
        self.btn_show_error_log.setText(QCoreApplication.translate('generals', 'Show error log'))
        self.newLayerGroupBox.setTitle(QCoreApplication.translate('generals', 'Upload xtf-log file'))
        self.existingLayerGroupBox.setTitle(QCoreApplication.translate('generals', 'Show log for existing layer'))
        self.existingLayerLabel.setText(QCoreApplication.translate('generals', 'Only layers created with this plugin can be selected'))
        self.dock = None
        self.errorLayer = None
        self.iface = iface
        self.txt_input.setText(file_path)
        self.txt_input.textChanged.connect(self.inputTextChanged)

    def showEvent(self, event):
        self.updateLayerCombobox()

    def getInputFile(self):
        self.btn_run.setEnabled(False)
        datei = QtWidgets.QFileDialog.getOpenFileName(None, 'Upload', filter="*.xtf")[0]
        self.txt_input.setText(datei)

    def inputTextChanged(self):
        if self.txt_input.text() == "":
            self.btn_run.setEnabled(False)
        else:
            self.btn_run.setEnabled(True)

    def visualizeLog(self):
        path = self.txt_input.text()
        fileName = None
        if(path.startswith("http")) or path.startswith("https"):
            try:
                xml_string = requests.get(path).content.decode("utf-8")
                if(len(xml_string)>5000000):
                    self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'Large file'),  QCoreApplication.translate('generals', 'Processing of large XTF-Log files might take a while'), duration=8)
                    self.iface.mainWindow().repaint()
                tree = ET.ElementTree(ET.fromstring(xml_string))
                fileName, _ = os.path.splitext(os.path.basename(path))

            except:
                self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'No valid file'), QCoreApplication.translate('generals', 'Could not get a valid XTF-Log file from specified Url'), duration=8)
        else:
            try:
                if(os.path.getsize(path)>5000000):
                    self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'Large file'),  QCoreApplication.translate('generals', 'Processing of large XTF-Log files might take a while'), duration=8)
                    self.iface.mainWindow().repaint()
                tree = ET.parse(path)
                fileName, fileExtension = os.path.splitext(os.path.basename(path))
            except:
                self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'No valid file'), QCoreApplication.translate('generals', 'No valid XTF-Log file at specified Path'), duration=8)

        if fileName != None:
            root = tree.getroot()
            
            # Check if INTERLIS 2.3. Model
            ns = {'ili': 'http://www.interlis.ch/INTERLIS2.3'}
            models_tag = root.find('.//ili:MODELS/ili:MODEL', namespaces=ns)
            if models_tag is not None:
                model_name = models_tag.get('NAME')
                if model_name == 'ErrorLog14':
                    self.visualizeLog_ig()
                    return
                elif model_name != 'IliVErrors':
                    self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', f'Unsupported error file version , Model {model_name} not supported yet - please contact developer if you are interested to add support for this model format!'), level=Qgis.Warning)
                    self.close()
                    return
            # Check if INTERLIS 2.4. Model
            # 3.7.2025 as interlis2.4 version will not find a models_tag
            else:
                # ns = {'ili': 'http://www.interlis.ch/INTERLIS2.4'}
                ns = {'ili': 'http://www.interlis.ch/xtf/2.4/INTERLIS'}
                # /ili:transfer/ili:headersection/ili:models/ili:model
                models_tag = root.find('.//ili:models/ili:model', namespaces=ns)
                models_senders = root.find('.//ili:sender', namespaces=ns)
                if models_tag is not None:
                    # model_name = models_tag.get('NAME')
                    model_name = models_tag.text
                    model_sender = models_senders.text
                    if model_sender == 'iG/Check':
                        self.visualizeLog24_ig()
                        #self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'Unsupported error file version interlis2.4, ErrorLog24 iG/Check not supported yet - please contact developer if you are interested to add support for this model format!'), level=Qgis.Warning)
                        #self.close()
                        return
                    elif model_sender == 'IliVErrors':
                        # iface.messageBar().pushMessage("Error", "I'm sorry Dave, I'm afraid I can't do that", level=Qgis.Warning)
                        self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'Unsupported error file version interlis2.4, ErrorLog24 IliVErrors not supported yet - please contact developer if you are interested to add support for this model format!'), level=Qgis.Warning)
                    else:
                        self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', f'Unsupported error file version interlis2.4, Model {model_name} / {model_sender} not supported yet - please contact developer if you are interested to add support for this model format!'), level=Qgis.Warning)
                self.close()
                return
            x = None
            y = None
            errorLayer = QgsVectorLayer("Point?crs=epsg:2056", fileName + "_Ilivalidator_Errors", "memory")
            errorDataProvider = errorLayer.dataProvider()

            errorDataProvider.addAttributes([QgsField("ErrorId", QMetaType.QString),
                                            QgsField("Type", QMetaType.QString),
                                            QgsField("Message", QMetaType.QString),
                                            QgsField("Description", QMetaType.QString),
                                            QgsField("Category", QMetaType.QString),
                                            QgsField("Tid", QMetaType.QString),
                                            QgsField("ObjTag", QMetaType.QString),
                                            QgsField("Model", QMetaType.QString),
                                            QgsField("TechId", QMetaType.QString),
                                            QgsField("Topic", QMetaType.QString),
                                            QgsField("UserId", QMetaType.QString),
                                            QgsField("Class", QMetaType.QString),
                                            QgsField("Name", QMetaType.QString),
                                            QgsField("Value", QMetaType.QString),
                                            QgsField("IliQName", QMetaType.QString),
                                            QgsField("DataSource", QMetaType.QString),
                                            QgsField("Line", QMetaType.QString),
                                            QgsField("TechDetails", QMetaType.QString),
                                            QgsField("Checked", QMetaType.Type.Int)])

            errorLayer.updateFields()

            # Hide Checked attribute from user
            setup = QgsEditorWidgetSetup('Hidden', {})
            error_idx = errorLayer.fields().indexFromName('Checked')
            errorLayer.setEditorWidgetSetup(error_idx, setup)

            # Remove layer if exists
            existing_error_layer = QgsProject.instance().mapLayersByName("Ilivalidator_errors")
            if len(existing_error_layer) != 0:
                QgsProject.instance().removeMapLayer(existing_error_layer[0])

            QgsProject.instance().addMapLayer(errorLayer)

            interlisPrefix = '{http://www.interlis.ch/INTERLIS2.3}'
            for child in root.iter(interlisPrefix + 'IliVErrors.ErrorLog.Error'):
                ErrorId = child.attrib["TID"]
                attributes = {}
                
                # Extract all specified attributes from the error element
                for attributeName in self.attributeNames:
                    element = child.find(interlisPrefix + attributeName)
                    attributes[attributeName] = (element.text if element is not None else "")
                
                # Process only 'Error' or 'Warning' types
                if attributes["Type"] == 'Error' or attributes["Type"] == 'Warning':
                    f = QgsFeature()
                    
                    # Try to extract geometry if available
                    GeometryElement = child.find(interlisPrefix + 'Geometry')
                    if GeometryElement is not None:
                        Coordinate = GeometryElement.find(interlisPrefix + 'COORD')
                        if Coordinate is not None:
                            x_elem = Coordinate.find(interlisPrefix + 'C1')
                            y_elem = Coordinate.find(interlisPrefix + 'C2')
                            if x_elem is not None and y_elem is not None:
                                try:
                                    x = float(x_elem.text)
                                    y = float(y_elem.text)
                                    # Set geometry as a point
                                    f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
                                except ValueError:
                                    pass  # Ignore invalid coordinate values
                    
                    # Set attribute values, including a default 'Checked' column (set to 0)
                    attributeList = [ErrorId]
                    attributeList.extend(list(attributes.values()))
                    attributeList.append(0)  # 0 means 'unchecked'
                    f.setAttributes(attributeList)

                    # Add feature to the data provider (layer)
                    errorDataProvider.addFeature(f)

            if(errorLayer.featureCount()== 0):
                QgsProject.instance().removeMapLayer(errorLayer)
                self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'No Errors'), QCoreApplication.translate('generals', 'The selected XTF file contains no Ilivalidator-Errors, select another file.'), level=Qgis.Info, duration=8)
                self.close()
                return

            errorLayer.updateExtents()
            self.errorLayer = errorLayer
            self.hideCheckedColumns(errorLayer)

            if(self.errorLayer != None):
                self.showDock()
            self.close()

    def visualizeLog_ig(self):
        def create_error_layer(layer_name, geometry_type):
            layer = QgsVectorLayer(f"{geometry_type}?crs=epsg:2056", layer_name, "memory")
            pr = layer.dataProvider()
            pr.addAttributes([
                QgsField("ErrorId", QMetaType.QString),
                QgsField("Type", QMetaType.QString),
                QgsField("Message", QMetaType.QString),
                QgsField("Description", QMetaType.QString),
                QgsField("Category", QMetaType.QString),
                QgsField("Tid", QMetaType.QString),
                QgsField("ObjTag", QMetaType.QString),
                QgsField("Model", QMetaType.QString),
                QgsField("TechId", QMetaType.QString),
                QgsField("Topic", QMetaType.QString),
                QgsField("UserId", QMetaType.QString),
                QgsField("Class", QMetaType.QString),
                QgsField("Name", QMetaType.QString),
                QgsField("Value", QMetaType.QString),
                QgsField("IliQName", QMetaType.QString),
                QgsField("DataSource", QMetaType.QString),
                QgsField("Line", QMetaType.QString),
                QgsField("TechDetails", QMetaType.QString),
                QgsField("Checked", QMetaType.Type.Int)
            ])
            layer.updateFields()
            # Hide 'Checked' attribute
            setup = QgsEditorWidgetSetup('Hidden', {})
            idx = layer.fields().indexFromName('Checked')
            layer.setEditorWidgetSetup(idx, setup)
            return layer

        path = self.txt_input.text()
        fileName = None
        tree = None

        if path.startswith("http") or path.startswith("https"):
            try:
                xml_string = requests.get(path).content.decode("utf-8")
                if len(xml_string) > 5000000:
                    self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'Large file'), QCoreApplication.translate('generals', 'Processing of large XTF-Log files might take a while'), duration=8)
                    self.iface.mainWindow().repaint()
                tree = ET.ElementTree(ET.fromstring(xml_string))
                fileName, _ = os.path.splitext(os.path.basename(path))
            except Exception as e:
                self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'No valid file'), QCoreApplication.translate('generals', 'Could not get a valid XTF-Log file from specified Url'), level=Qgis.Warning, duration=8)
                return
        else:
            try:
                if os.path.getsize(path) > 5000000:
                    self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'Large file'), QCoreApplication.translate('generals', 'Processing of large XTF-Log files might take a while'), level=Qgis.Info, duration=15)
                    self.iface.mainWindow().repaint()
                tree = ET.parse(path)
                fileName, _ = os.path.splitext(os.path.basename(path))
            except Exception as e:
                self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'No valid file'), QCoreApplication.translate('generals', 'No valid XTF-Log file at specified Path'), level=Qgis.warning, duration=8)
                return

        if fileName is None:
            return

        root = tree.getroot()
        interlisPrefix = '{http://www.interlis.ch/INTERLIS2.3}'
        ns = {'ig': 'http://www.interlis.ch/INTERLIS2.3'}

        # Step 1: Detect which types exist
        has_point = False
        has_line = False
        has_surface = False
        has_nogeom = False

        for child in root.iter(interlisPrefix + 'ErrorLog14.Errors.Error'):
            geom_element = child.find(interlisPrefix + 'Geom')
            if geom_element is not None and len(geom_element) > 0:
                LogType = geom_element[0].tag.split('.')[-1]
                if LogType == 'PointGeometry':
                    has_point = True
                elif LogType == 'LineGeometry':
                    has_line = True
                elif LogType == 'SurfaceGeometry':
                    has_surface = True
            else:
                has_nogeom = True

        if not (has_point or has_line or has_surface):
            self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'No valid geometry'), QCoreApplication.translate('generals', '11No Point, Line or Surface Geometries found.'), duration=8)
            return

        # Step 2: Create layers
        point_layer = create_error_layer(fileName + "_igChecker_Points", "Point") if has_point else None
        line_layer = create_error_layer(fileName + "_igChecker_Lines", "LineString") if has_line else None
        polygon_layer = create_error_layer(fileName + "_igChecker_Surfaces", "Polygon") if has_surface else None
        no_geom_layer = create_error_layer(fileName + "_igChecker_NoGeometry", "None") if has_nogeom else None
        # Step 3: Insert features
        for child in root.iter(interlisPrefix + 'ErrorLog14.Errors.Error'):
            ErrorId = child.attrib["TID"]
            attributes = {}
            for attributeName in self.attributeNames:
                element = child.find(interlisPrefix + attributeName)
                attributes[attributeName] = (element.text if element is not None else "")
            # add name and value for attributes
            user_attributes = child.find(interlisPrefix + 'UserAttributes')
            if user_attributes is not None:
                for user_attr in user_attributes.findall(interlisPrefix + 'ErrorLog14.Errors.Attribute'):
                    name_element = user_attr.find(interlisPrefix + 'Name')
                    value_element = user_attr.find(interlisPrefix + 'Value')
                    attributes['Name'] = name_element.text
                    attributes['Value'] = value_element.text


            if attributes["Category"] not in ['error', 'warning','info']:
                continue

            geom_element = child.find(interlisPrefix + 'Geom')

            if geom_element is None or len(geom_element) == 0:
                if no_geom_layer:
                    attributeList = [ErrorId]
                    attributeList.extend(list(attributes.values()))
                    attributeList.append(0)
                    f.setAttributes(attributeList)
                    no_geom_layer.dataProvider().addFeature(f)
                continue

            LogType = geom_element[0].tag.split('.')[-1]
            f = QgsFeature()

            if LogType == 'PointGeometry' and point_layer:
                coordinate = geom_element[0][0][0]
                if coordinate is not None:
                    x = coordinate.find(interlisPrefix + 'C1').text
                    y = coordinate.find(interlisPrefix + 'C2').text
                    if x and y:
                        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(x), float(y))))
                        attributeList = [ErrorId]
                        attributeList.extend(list(attributes.values()))
                        attributeList.append(0)  # Checked
                        f.setAttributes(attributeList)
                        point_layer.dataProvider().addFeature(f)

            elif LogType == 'LineGeometry' and line_layer:
                polyline = child.find('.//ig:Geom/ig:POLYLINE', namespaces=ns)
                if polyline is not None:
                    points = []
                    for coord in polyline.findall(interlisPrefix + 'COORD'):
                        x = coord.find(interlisPrefix + 'C1').text
                        y = coord.find(interlisPrefix + 'C2').text
                        points.append(QgsPointXY(float(x), float(y)))
                    if points:
                        f.setGeometry(QgsGeometry.fromPolylineXY(points))
                        attributeList = [ErrorId]
                        attributeList.extend(list(attributes.values()))
                        attributeList.append(0)
                        f.setAttributes(attributeList)
                        line_layer.dataProvider().addFeature(f)

            elif LogType == 'SurfaceGeometry' and polygon_layer:
                polyline = child.find('.//ig:Geom/ig:SURFACE/ig:BOUNDARY/ig:POLYLINE', namespaces=ns)
                if polyline is not None:
                    points = []
                    for coord in polyline.findall(interlisPrefix + 'COORD'):
                        x = coord.find(interlisPrefix + 'C1').text
                        y = coord.find(interlisPrefix + 'C2').text
                        points.append(QgsPointXY(float(x), float(y)))
                    if points:
                        f.setGeometry(QgsGeometry.fromPolygonXY([points]))
                        attributeList = [ErrorId]
                        attributeList.extend(list(attributes.values()))
                        attributeList.append(0)
                        f.setAttributes(attributeList)
                        polygon_layer.dataProvider().addFeature(f)

        # Step 4: Add layers to project
        if point_layer and point_layer.featureCount() > 0:
            point_layer.updateExtents()
            QgsProject.instance().addMapLayer(point_layer)
        if line_layer and line_layer.featureCount() > 0:
            line_layer.updateExtents()
            QgsProject.instance().addMapLayer(line_layer)
        if polygon_layer and polygon_layer.featureCount() > 0:
            polygon_layer.updateExtents()
            QgsProject.instance().addMapLayer(polygon_layer)
        if no_geom_layer and no_geom_layer.featureCount() > 0:
            no_geom_layer.updateExtents()
            QgsProject.instance().addMapLayer(no_geom_layer)

        if not ((point_layer and point_layer.featureCount() > 0) or
                (line_layer and line_layer.featureCount() > 0) or
                (polygon_layer and polygon_layer.featureCount() > 0) or
                (no_geom_layer and no_geom_layer.featureCount() > 0)):
            
            self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'No Errors'), QCoreApplication.translate('generals', 'The selected XTF file contains no igCheck-Errors, select another file.'), level=Qgis.Info, duration=8)
            return

        # optional: store last used layer
        self.errorLayer = point_layer or line_layer or polygon_layer or no_geom_layer
        if self.errorLayer:
            self.showDock()
        self.close()

    def visualizeLog24_ig(self):
        def create_error_layer(layer_name, geometry_type):
            layer = QgsVectorLayer(f"{geometry_type}?crs=epsg:2056", layer_name, "memory")
            pr = layer.dataProvider()
            pr.addAttributes([
                QgsField("ErrorId", QMetaType.QString),
                QgsField("Type", QMetaType.QString),
                QgsField("Message", QMetaType.QString),
                QgsField("Description", QMetaType.QString),
                QgsField("Category", QMetaType.QString),
                QgsField("Tid", QMetaType.QString),
                QgsField("ObjTag", QMetaType.QString),
                QgsField("Model", QMetaType.QString),
                QgsField("TechId", QMetaType.QString),
                QgsField("Topic", QMetaType.QString),
                QgsField("UserId", QMetaType.QString),
                QgsField("Class", QMetaType.QString),
                QgsField("Name", QMetaType.QString),
                QgsField("Value", QMetaType.QString),
                QgsField("IliQName", QMetaType.QString),
                QgsField("DataSource", QMetaType.QString),
                QgsField("Line", QMetaType.QString),
                QgsField("TechDetails", QMetaType.QString),
                QgsField("Checked", QMetaType.Type.Int)
            ])
            layer.updateFields()
            # Hide 'Checked' attribute
            setup = QgsEditorWidgetSetup('Hidden', {})
            idx = layer.fields().indexFromName('Checked')
            layer.setEditorWidgetSetup(idx, setup)
            return layer

        path = self.txt_input.text()
        fileName = None
        tree = None

        if path.startswith("http") or path.startswith("https"):
            try:
                xml_string = requests.get(path).content.decode("utf-8")
                if len(xml_string) > 5000000:
                    self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'Large file'), QCoreApplication.translate('generals', 'Processing of large XTF-Log files might take a while'), duration=8)
                    self.iface.mainWindow().repaint()
                tree = ET.ElementTree(ET.fromstring(xml_string))
                fileName, _ = os.path.splitext(os.path.basename(path))
            except Exception as e:
                self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'No valid file'), QCoreApplication.translate('generals', 'Could not get a valid XTF-Log file from specified Url'), level=Qgis.Warning, duration=8)
                return
        else:
            try:
                if os.path.getsize(path) > 5000000:
                    self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'Large file'), QCoreApplication.translate('generals', 'Processing of large XTF-Log files might take a while'), level=Qgis.Info, duration=15)
                    self.iface.mainWindow().repaint()
                tree = ET.parse(path)
                fileName, _ = os.path.splitext(os.path.basename(path))
            except Exception as e:
                self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'No valid file'), QCoreApplication.translate('generals', 'No valid XTF-Log file at specified Path'), level=Qgis.warning, duration=8)
                return

        if fileName is None:
            return

        root = tree.getroot()
        namespaces = {
            'ili': 'http://www.interlis.ch/xtf/2.4/INTERLIS',
            'geom': 'http://www.interlis.ch/geometry/1.0',
            'default': 'http://www.infogrips.ch/INTERLIS/2.4/ErrorLog24'
        }
        interlisPrefix = '{http://www.infogrips.ch/INTERLIS/2.4/ErrorLog24}'
        # Step 1: Detect which types exist
        has_point = False
        has_line = False
        has_surface = False
        has_nogeom = False

        for child in root.iter(interlisPrefix +'Error'):
            LogType = child.find('.//default:Geom', namespaces)[0].tag.split('}')[1]
            if LogType is not None and len(LogType) > 0:
                if LogType == 'PointGeometry':
                    has_point = True
                elif LogType == 'LineGeometry':
                    has_line = True
                elif LogType == 'SurfaceGeometry':
                    has_surface = True
            else:
                has_nogeom = True

        if not (has_point or has_line or has_surface):
           self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'No valid geometry'), QCoreApplication.translate('generals', 'No Point, Line or Surface Geometries found.'), duration=8)
           return

        # Step 2: Create layers
        point_layer = create_error_layer(fileName + "_igChecker24_Points", "Point") if has_point else None
        line_layer = create_error_layer(fileName + "_igChecker24_Lines", "LineString") if has_line else None
        polygon_layer = create_error_layer(fileName + "_igChecker24_Surfaces", "Polygon") if has_surface else None
        no_geom_layer = create_error_layer(fileName + "_igChecker24_NoGeometry", "None") if has_nogeom else None
        
        # Step 3: Insert features
        for child in root.iter(interlisPrefix +'Error'):
            ErrorId = child.attrib.get('{http://www.interlis.ch/xtf/2.4/INTERLIS}tid', '')
            attributes = {}
            for attributeName in self.attributeNames:
                element = child.find( interlisPrefix + attributeName)
                attributes[attributeName] = (element.text if element is not None else "")

            if attributes["Category"] not in ['error', 'warning','info']:
                continue
            
            
            geom_element = child.find('.//default:Geom', namespaces)
            if geom_element is None or len(geom_element) == 0:
                if no_geom_layer:
                    attributeList = [ErrorId]
                    attributeList.extend(list(attributes.values()))
                    attributeList.append(0)
                    f.setAttributes(attributeList)
                    no_geom_layer.dataProvider().addFeature(f)
                continue

            f = QgsFeature()

            LogType = child.find('.//default:Geom', namespaces)[0].tag.split('}')[1]
            if LogType == 'PointGeometry' and point_layer:
                #coordinate = None
                if geom_element is not None:
                    x = child.find('.//geom:c1',namespaces).text
                    y = child.find('.//geom:c2',namespaces).text
                    if x and y:
                        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(x), float(y))))
                        attributeList = [ErrorId]
                        attributeList.extend(list(attributes.values()))
                        attributeList.append(0)  # Checked
                        f.setAttributes(attributeList)
                        point_layer.dataProvider().addFeature(f)

            elif LogType == 'LineGeometry' and line_layer:
                polyline = child.find('.//ig:Geom/ig:POLYLINE', namespaces)
                if polyline is not None:
                    points = []
                    for coord in polyline.findall(interlisPrefix + 'COORD'):
                        x = coord.find(interlisPrefix + 'C1').text
                        y = coord.find(interlisPrefix + 'C2').text
                        points.append(QgsPointXY(float(x), float(y)))
                    if points:
                        f.setGeometry(QgsGeometry.fromPolylineXY(points))
                        attributeList = [ErrorId]
                        attributeList.extend(list(attributes.values()))
                        attributeList.append(0)
                        f.setAttributes(attributeList)
                        line_layer.dataProvider().addFeature(f)

            elif LogType == 'SurfaceGeometry' and polygon_layer:
                polyline = child.find('.//ig:Geom/ig:SURFACE/ig:BOUNDARY/ig:POLYLINE', namespaces)
                if polyline is not None:
                    points = []
                    for coord in polyline.findall(interlisPrefix + 'COORD'):
                        x = coord.find(interlisPrefix + 'C1').text
                        y = coord.find(interlisPrefix + 'C2').text
                        points.append(QgsPointXY(float(x), float(y)))
                    if points:
                        f.setGeometry(QgsGeometry.fromPolygonXY([points]))
                        attributeList = [ErrorId]
                        attributeList.extend(list(attributes.values()))
                        attributeList.append(0)
                        f.setAttributes(attributeList)
                        polygon_layer.dataProvider().addFeature(f)

        # Step 4: Add layers to project
        if point_layer and point_layer.featureCount() > 0:
            point_layer.updateExtents()
            QgsProject.instance().addMapLayer(point_layer)
        if line_layer and line_layer.featureCount() > 0:
            line_layer.updateExtents()
            QgsProject.instance().addMapLayer(line_layer)
        if polygon_layer and polygon_layer.featureCount() > 0:
            polygon_layer.updateExtents()
            QgsProject.instance().addMapLayer(polygon_layer)
        if no_geom_layer and no_geom_layer.featureCount() > 0:
            no_geom_layer.updateExtents()
            QgsProject.instance().addMapLayer(no_geom_layer)

        if not ((point_layer and point_layer.featureCount() > 0) or
                (line_layer and line_layer.featureCount() > 0) or
                (polygon_layer and polygon_layer.featureCount() > 0) or
                (no_geom_layer and no_geom_layer.featureCount() > 0)):
            
            self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'No Errors'), QCoreApplication.translate('generals', '33The selected XTF file contains no igCheck-Errors, select another file.'), level=Qgis.Info, duration=8)
            return

        # optional: store last used layer
        self.errorLayer = point_layer or line_layer or polygon_layer or no_geom_layer
        if self.errorLayer:
            self.showDock()
        self.close()



    def showErrorLog(self):
        for layer in QgsProject.instance().mapLayers().values():
            if layer.name() == self.layerbox.currentText():
                self.errorLayer = layer
                self.showDock()

    def hideCheckedColumns(self, layer):
        config = layer.attributeTableConfig()
        columns = config.columns()
        for column in columns:
            if column.name == "Checked":
                column.hidden = True
                break
        config.setColumns(columns)
        layer.setAttributeTableConfig(config)

    def updateLayerCombobox(self):
        self.layerbox.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsMapLayerType.VectorLayer:
                if all(x in layer.fields().names() for x in self.attributeNames):
                    self.layerbox.addItem(layer.name())

    def showDock(self):
        for dock in self.iface.mainWindow().findChildren(XTFLog_DockPanel):
            self.iface.removeDockWidget(dock)
        if "_igChecker" in self.errorLayer.name():
            self.dock = XTFLog_igCheck_DockPanel(self.iface, self.errorLayer)
        else:
            self.dock = XTFLog_DockPanel(self.iface, self.errorLayer)
        self.iface.addTabifiedDockWidget(Qt.RightDockWidgetArea, self.dock, raiseTab=True)
        self.close()



    def closePlugin(self):
        self.close()
        if self.dock != None:
            self.iface.removeDockWidget(self.dock)
