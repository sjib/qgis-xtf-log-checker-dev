# XTFLog-Checker

## What do I use XTFLog-Checker for?
XTFLog-Checker is a [QGIS](https://www.qgis.org/en/site/) plugin that lets you display errors in XTFLog files created by the [Ilivalidator](https://www.interlis.ch/downloads/ilivalidator) and [iG/Check](https://www.interlis.ch/en/downloads/igcheck). When opening an XTFLog file in QGIS with this plugin, a checklist is created that helps you keep track of your progress when addressing the errors.

## Where can I get it?
Install the [QGIS XTFLog-Checker](https://plugins.qgis.org/plugins) directly in QGIS by using the [Plugins menu](http://docs.qgis.org/latest/en/docs/user_manual/plugins/plugins.html).

## Qt6 supported
Beginning with version 1.30, Qt6 support has been added. The plugin is now compatible with both Qt5 and Qt6 builds of QGIS.
As QGIS based on Qt6 is still in its early testing phase, some bugs may occur.
Please report any problems you experience by submitting an issue.

## Requirements
- QGIS version: 3.40 or later
- Tested on Windows, macOS, and Linux

## How to use

1. Click on the XTFLog-Checker Icon <img src='screenshots/xtflogchecker_icon.png' alt="Icon" >

The following dialog will appear:

<img src='screenshots/xtflogchecker_dialog.png' alt="Icon" width="60%">

2. A. Select the error log xtf file you want to be visualized.

<img src='screenshots/xtflogchecker_dialog2.png' alt="Icon" width="60%">

   B. You can also load an XTF URL by copying the address and pasting it into the input box.
<img src='screenshots/xtflogchecker_url_input_box.png' alt="Icon" width="60%">

C. You can also load a URL from an online validation service, such as [ilicop.ch](https://ilicop.ch/).
<img src='screenshots/xtflogchecker_url_input_box2.png' alt="Icon" width="60%">

3. Click on 'Create Layer' - the error log will be analyzed and the results will be displayed.

4. Use the **Layer Switch** dropdown or reopen the dialog to change layers.

### Ilivalidator

<img src='screenshots/xtflogchecker_ilivalidator_errors.png' alt="Icon" width="90%">

All Errors are displayed on the same layer. The latest version also supports the display of Errors without an assigned geometry. 


### iG/Check

<img src='screenshots/xtflogchecker_igcheck_errors.png' alt="Icon" width="90%">

Since Release 1.1.0 also iG/Check Errors logs are supported. For each Geometry type an extra layer is created and connected with the respective errors. There are four possible layers:

   * NoGeometry
   * Points
   * Lines
   * Surfaces

The following INTERLIS Error log versions are supported: 
https://www.infogrips.ch/models/2.3/ErrorLog14.ili (since release 1.1.0)
and https://www.infogrips.ch/models/2.4/ErrorLog24.ili (since release 1.2.0)



### Change layer

Click on the XTFLog-Checker Icon <img src='screenshots/xtflogchecker_icon.png' alt="Icon" > again

In the following dialog choose the layer you want to be displayed:

<img src='screenshots/xtflogchecker_dialog_change_layer.png' alt="Icon" width="60%">

Or you can change the layer from the “Layer Switch” dropdown in the panel.

<img src='screenshots/xtflogchecker_dialog_change_layer2.png' alt="Icon" width="60%">

### Filter errors by category

You can filter the errors by their categories: [errors, warnings, info]:

<img src='screenshots/xtflogchecker_filter_error_warning.png' alt="Icon" width="90%">

<img src='screenshots/xtflogchecker_filter_info.png' alt="Icon" width="90%">

### Advanced selection
You can also use the advanced selection, to choose Class,Tid,Topic,ErrorId,Description,After selecting, the first item will be automatically highlighted and zoomed in.

<img src='screenshots/xtflogchecker_advanced_selection.png' alt="Icon" width="60%">

### Select All and Clear All buttons

You can use the 'Select All' button to select all items in the current list.
<img src='screenshots/xtflogchecker_select_all.png' alt="Icon" width="90%">

'Clear All' will deselect all items.
<img src='screenshots/xtflogchecker_clear_all.png' alt="Icon" width="90%">

### Tooltip with additional information

When hovering over an entry, a floating box appears displaying the corresponding TID, Module, Error_ID, Model, Description, Topic, Class, Tid, Name, and Value information. 

<img src='screenshots/xtflogchecker_tooltip.png' alt="Icon" width="60%">


Further details you get by opening the attribute table of the respective layer
<img src='screenshots/xtflogchecker_attribute_table.png' alt="Icon" width="90%">

## License
The XTFLog-Checker plugin is licensed under the [GPL-3.0 license](LICENSE).  
Copyright © 2025
[GeoWerkstatt GmbH](https://www.geowerkstatt.ch) & [Stefan Jürg Burckhardt, Software, Informationsmanagement, Beratung (SJiB)](https://www.sjib.ch/)
