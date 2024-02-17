#copyright - Rohit Nair
#This tool optimizes a scene and groups and saves the optimized nodes[renames them] as a separate file with _lo extension to the name 
#in the same location as the original file and creates a perforce change list and adds the newly created file to it
#It also creates a json file which includes the percentagereduction data and the UUIDs for every mesh
#This can be used for batch reduction later on
#To use this tool, InstaLOD needs to be integrated into the userSetup.mel file and needs to be setup in Maya


from PyQt5.QtWidgets import (QMainWindow, QPushButton, QVBoxLayout,
                             QWidget, QFrame, QSlider, QLabel, 
                             QApplication)
from PyQt5.QtGui import QFont
from PyQt5 import QtCore
import json
import pymel.core as pm
from maya import cmds
import maya.OpenMayaUI as omui
import os
from P4 import P4

class MeshOptimizerWindow(QMainWindow):
    def __init__(self):
        super(MeshOptimizerWindow, self).__init__()
        
    # UI Setup
        self.setWindowTitle("Hair Optimizer")
        self.resize(500, 200) 

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        self.slider = QSlider()
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setSingleStep(1)
        self.slider.setTickInterval(10)
        self.slider.setTickPosition(
    QSlider.TicksBelow)
        self.slider.setStyleSheet(
    "QSlider::groove:horizontal { "
    "background: #dddddd; border: "
    "1px solid #777; height: 10px; "
    "border-radius: 4px; } "
    "QSlider::handle:horizontal { "
    "background: #007BFF; border: "
    "1px solid #0056b3; width: 18px; "
    "margin-top: -3px; margin-bottom: "
    "-3px; border-radius: 9px; }")
        self.slider.valueChanged.connect(
        self.sliderValueChanged)
        self.slider.setOrientation(
    QtCore.Qt.Horizontal)
        layout.addWidget(self.slider)

        
        self.label = QLabel("0")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.label.setFont(font)

        self.btn = QPushButton(
    "Export Reduction")
        self.btn.setStyleSheet(
    "QPushButton { background-color: #007BFF; "
    "color: white; border: none; padding: "
    "10px 20px; border-radius: 5px; } "
    "QPushButton:hover { background-color: "
    "#0056b3; }")
        self.btn2 = QPushButton(
    "Optimize Mesh")
        self.btn2.setStyleSheet(
    "QPushButton { background-color: #007BFF; "
    "color: white; border: none; padding: "
    "10px 20px; border-radius: 5px; } "
    "QPushButton:hover { background-color: "
    "#0056b3; }")
        self.btn.clicked.connect(
        self.write_json_file)
        self.btn2.clicked.connect(
    self.Final_Optimize)

        layout.addWidget(self.label)
        layout.addWidget(self.btn)
        layout.addWidget(self.btn2)
    
    #Creates a JSON file containing the reduction percentage and 
    #UUIDs of the meshes in the scene, 
    #then saves it in the original file location.
    def write_json_file(self):
        original_file_path = cmds.file(q=True, sceneName=True)
        mesh_transforms = cmds.ls(type='transform')
        uuids = []
        for obj in mesh_transforms:
            children = cmds.listRelatives(obj, children=True, type='mesh') or []
            for child in children:
                uuid = cmds.ls(child, uuid=True)[0]
                uuids.append(uuid)
        data = {
            "reduction_percentage": self.slider.value(),
            "uuids": uuids
        }        
        file_name = os.path.basename(original_file_path)
        dir_name = os.path.dirname(original_file_path)
        file_name_without_extension = os.path.splitext(file_name)[0]
        json_file_name = file_name_without_extension + '.json'
        json_file_path = os.path.join(dir_name, json_file_name)
        with open(json_file_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)            
                
    #Initiates the final optimization process for meshes, 
    #including renaming and saving the optimized file   
    def Final_Optimize(self):
        mesh_group_name = self.get_mesh_group_name()
        mesh_transforms = self.list_mesh_transforms()
        self.optimize_and_rename(mesh_transforms)
        new_file_path = self.create_lo_file(mesh_group_name, mesh_transforms)
        self.create_perforce_changelist(new_file_path, "Mesh Optimization")
        
    #Updates the label text with the current value of the slider.
    def sliderValueChanged(self, value):
        self.label.setText(str(value))
        
    #Retrieves the name of the mesh group from the scene.    
    def get_mesh_group_name(self):
        transform_nodes = pm.ls(type='transform')
        for transform_node in transform_nodes:
            if transform_node.listRelatives(ad=True, type='mesh'):
                return transform_node.getParent()
            else:
                pm.warning("No mesh group found in the scene.")
                
    #Lists all the transform nodes that have mesh children.    
    def list_mesh_transforms(self):
        mesh_transforms = []
        all_objects = pm.ls(type='transform')
        for obj in all_objects:
            children = obj.getChildren(type='mesh')
            if children:
                mesh_transforms.append(obj)
        return mesh_transforms
    
    #Optimizes meshes using InstaLOD and renames them.
    def optimize_and_rename(self, mesh_transforms): 
        for transform_node in mesh_transforms:
            pm.optionVar(query='INSTALOD_ID_OP_PERCENTTRIANGLES')
            pm.mel.eval("InstaLOD_ResetSettings(false);")
            pm.optionVar(stringValue=
            ('INSTALOD_ID_OPTIMIZE_TYPE', "Optimize"))
            pm.optionVar(floatValue=('INSTALOD_ID_OP_PERCENTTRIANGLES', 
                                     float(self.slider.value())))
            pm.mel.eval("InstaLOD_OptimizeMesh(\"{0}\", \"\", false);"
                        .format(transform_node))
            optimized_meshes = pm.ls(type='mesh', transforms=True)
            for mesh in optimized_meshes:
                new_name = mesh.name().replace("INSTALOD_", "")
                new_name = new_name + "_lo"
                pm.rename(mesh, new_name)
                
    #Creates a new Maya ascii file containing the optimized meshes.
    def create_lo_file(self, mesh_group_name, mesh_transforms):
        original_file_path = pm.sceneName()
        pm.newFile(force=True)
        lo_group_name = mesh_group_name + "_lo"
        lo_group = pm.group(empty=True, name=lo_group_name)
        lo_objects = pm.ls(regex=".*_lo", dag=True)
        pm.select(lo_objects)
        pm.parent(lo_objects, lo_group)
        original_dir = os.path.dirname(original_file_path)
        new_file_path = os.path.join(original_dir, 
                                     os.path.splitext
                                     (os.path.basename(original_file_path))[0] 
                                     + "_lo.ma")
        pm.saveAs(new_file_path)
        return new_file_path
        
    #Adds the optimized file to a Perforce changelist 
    def create_perforce_changelist(self, new_file_path, changelist_description):
        p4.run("change", "-o")
        changelist = p4.fetch_change()
        changelist["Description"] = changelist_description
        changelist = p4.save_change(changelist)
        p4.run("reopen", "-c", changelist, new_file_path)

#Returns the main Maya window as a QMainWindow instance.
def maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(long(main_window_ptr), QMainWindow)


def launch():
    global win
    try:
        win.close()
    except:
        pass
    win = MeshOptimizerWindow()
    win.show()


if __name__ == "__main__":
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    win = None
    launch()
