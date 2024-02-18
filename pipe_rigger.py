#copyright - Rohit Nair
#This is a rigging tool that takes a mesh and 
#creates a curve passing through the 
#centroids of its height subdivisions,
#then creates a joint chain along the curve 
#and binds the joint chain with the mesh 
#and animates it

import maya.OpenMaya as OpenMaya
import pymel.core as pm
import maya.cmds as cmds
from PyQt5.QtWidgets import QApplication, \
                            QMainWindow, \
                            QVBoxLayout, \
                            QWidget, \
                            QLabel, \
                            QPushButton, \
                            QLineEdit, \
                            QComboBox

#Defines the main window class for the Pipe Rigger tool
class PipeRiggerWindow(QMainWindow):
    def __init__(self):
        super(PipeRiggerWindow, self).__init__()

        #Set window properties
        self.setWindowTitle("Pipe Rigger")
        self.setGeometry(100, 100, 600, 500)

        #Set central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        #Add ComboBox for curve subdivisions
        subdivisions_label = QLabel('Curve Subdivisions')
        self.layout.addWidget(subdivisions_label)
        self.subdivisions_menu = QComboBox()
        self.subdivisions_menu.addItems([str(i) for i in range(1, 31)])
        self.layout.addWidget(self.subdivisions_menu)
        self.subdivisions_menu.currentIndexChanged.connect(self.update_label)

        #Add button to create curve
        self.create_curve_button = QPushButton("Create Curve")
        self.create_curve_button.clicked.connect(self.create_curve)
        self.create_curve_button.setStyleSheet("background-color: #2ecc71")
        self.layout.addWidget(self.create_curve_button)

        #Add ComboBox for joints
        joints_label = QLabel('Joints')
        self.layout.addWidget(joints_label)
        self.joints_menu = QComboBox()
        self.joints_menu.addItems([str(i) for i in range(1, 15)])
        self.layout.addWidget(self.joints_menu)
        self.joints_menu.currentIndexChanged.connect(self.update_label)

        #Add button to create joints and bind
        self.create_joints_button = QPushButton("Create Joints and Bind")
        self.create_joints_button.clicked.connect(self.create_joints_and_bind)
        self.create_joints_button.setStyleSheet("background-color: #27ae60")
        self.layout.addWidget(self.create_joints_button)

        #Add widgets for animation settings
        animation_settings_label = QLabel("Animation Settings:")
        self.layout.addWidget(animation_settings_label)
        start_frame_label = QLabel("Start Frame:")
        self.layout.addWidget(start_frame_label)
        self.start_frame_input = QLineEdit()
        self.layout.addWidget(self.start_frame_input)
        end_frame_label = QLabel("End Frame:")
        self.layout.addWidget(end_frame_label)
        self.end_frame_input = QLineEdit()
        self.layout.addWidget(self.end_frame_input)
        frame_step_label = QLabel("Frame Step:")
        self.layout.addWidget(frame_step_label)
        self.frame_step_input = QLineEdit()
        self.layout.addWidget(self.frame_step_input)

        #Add button to start animation
        self.animate_button = QPushButton("Animate")
        self.animate_button.clicked.connect(self.final_animation)
        self.animate_button.setStyleSheet("background-color: #1abc9c")
        self.layout.addWidget(self.animate_button)
        
    #Function to create a curve through centroids 
    #and delete Control vertices
    def create_curve_through_centroids_and_delete_cv(mesh, num_subdivisions):
        #Function to get the positions of vertices 
        #of the given mesh
        def get_vertex_positions(mesh):
            vertices = pm.polyListComponentConversion(mesh, tv=True)
            vertex_positions = pm.ls(vertices, flatten=True)
            return [pm.pointPosition(v) for v in vertex_positions]
        
        #Calculate centroid of a set of vertices
        def calculate_centroid(vertices):
            num_vertices = len(vertices)
            if num_vertices == 0:
                return None
            sum_position = sum(vertices, OpenMaya.MVector())
            centroid = sum_position / num_vertices
            return centroid

        #curve passing through centroids of height subdivisions
        vertices = get_vertex_positions(mesh)
        num_vertices = len(vertices)
        if num_vertices < 3:
            pm.warning("Selected object doesn't have enough vertices.")
            return

        step = num_vertices // num_subdivisions
        centroids = []

        #Calculate centroids of height subdivisions
        for i in range(0, num_vertices, step):
            subdivision = vertices[i:i+step]
            centroid = calculate_centroid(subdivision)
            if centroid:
                centroids.append(centroid)

        #Create a curve passing through centroids
        curve = pm.curve(d=1, p=[(c.x, c.y, c.z) for c in centroids])
        return curve
        
    #Function to delete certain curve control vertex
    def delete_specific_control_vertices_of_curves():
        curve_shapes = pm.ls(type='nurbsCurve')
        curve_transforms = [curve.getTransform() for curve in curve_shapes]
        curve_transforms = list(set(curve_transforms))
        pm.select(curve_transforms)
        pm.select(curve_transforms)
        pm.select(curve.cv[-1])
        pm.delete()
        
    #Function to create joint chain on curve
    def create_joint_chain_on_curve(curve, num_joints):
        #Function to get curve length
        def get_curve_length(curve):
            curve_cvs = curve.getCVs(space='world')
            curve_length = 0.0
            for i in range(len(curve_cvs) - 1):
                curve_length += (curve_cvs[i + 1] - curve_cvs[i]).length()
            return curve_length

        curve_length = get_curve_length(curve)
        spacing = curve_length / (num_joints - 1)
        joint_chain = []

        for i in range(num_joints):
            param = curve.getKnotDomain()[0] + \
            i * (curve.getKnotDomain()[1] - \
            curve.getKnotDomain()[0]) / (num_joints - 1)
            point_on_curve = pm.pointOnCurve(curve, 
                                             parameter=param, 
                                             turnOnPercentage=False)
            joint = pm.createNode('joint', 
                                   name='joint_{:02d}'.format(i + 1))
            joint.translate.set(point_on_curve)
            joint_chain.append(joint)

        for i in range(1, num_joints):
            pm.joint(joint_chain[i - 1], 
                     e=True, zeroScaleOrient=True, 
                     orientJoint='xyz', 
                     secondaryAxisOrient='yup')

        for i in range(1, num_joints):
            pm.parent(joint_chain[i], joint_chain[i - 1])

        pm.select(joint_chain[0])

    #Function to reroot joint chain
    def reroot_joint_chain():
        joints = pm.ls(type='joint')
        if joints:
            last_joint = joints[-1]
            pm.select(last_joint)
        else:
            print("No joints found in the scene.")
        mel.eval("RerootSkeleton;")

    #Function to create skin cluster
    def create_skin_cluster():
        meshes = pm.ls(tr=True, type='mesh')
        if not meshes:
            print("No meshes found.")
            return

        mesh_name = meshes[1] if len(meshes) >= 2 else meshes[0]
        mesh = pm.PyNode(mesh_name)

        mesh.select()

        joints = pm.ls(type="joint")
        if not joints:
            print("No joints found.")
            return

        pm.select(joints, add=True)

        skin_cluster = pm.skinCluster(joints, 
                                      mesh, 
                                      toSelectedBones=True, 
                                      bindMethod=0, 
                                      normalizeWeights=1)
        return skin_cluster

    #Function to animate joint chain randomly, 
    #you can add your desired animation code here
    def animate_joint_chain(self, start_frame, end_frame, frame_step):
        pm.select(deselect=True)
        joint_chain = pm.ls(type='joint')
        pm.select(joint_chain)

        for frame in range(start_frame, end_frame, frame_step):
            pm.currentTime(frame, edit=True)
            for joint in joint_chain:
                joint.rotateX.set(45 * frame)
                joint.rotateY.set(30 * frame)
                joint.rotateZ.set(15 * frame)
                pm.setKeyframe(joint, attribute='rotate')
        pm.playbackOptions(minTime=start_frame, maxTime=end_frame)

    #Method to update label
    def update_label(self, value):
        print("Selected value:", value)

    #Method to create curve
    def create_curve(self):
        selected_objects = pm.ls(sl=True)
        if not selected_objects:
            pm.warning("Please select a mesh.")
        else:
            mesh = selected_objects[0]
            num_subdivisions = self.update_label  # You can adjust this value as needed
            curve = create_curve_through_centroids_and_delete_cv(mesh, num_subdivisions)
            if curve:
                print("Curve created successfully.")
            delete_specific_control_vertices_of_curves()

    #Method to create joints and bind
    def create_joints_and_bind(self):
        curve = pm.ls(selection=True)[0]
        num_joints = self.update_label
        create_joint_chain_on_curve(curve, num_joints)
        reroot_joint_chain()
        create_skin_cluster()

    #Method to perform final animation
    def final_animation(self):
        start_frame = int(self.start_frame_input.text())
        end_frame = int(self.end_frame_input.text())
        frame_step = int(self.frame_step_input.text())
        self.animate_joint_chain(start_frame, end_frame, frame_step)

#Function to get the main Maya window
def maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(long(main_window_ptr), QMainWindow)

#Function to launch the Pipe Rigger tool
def launch():
    global win
    try:
        win.close()
    except:
        pass
    win = PipeRiggerWindow()
    win.show()

if __name__ == "__main__":
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    win = None
    launch()
