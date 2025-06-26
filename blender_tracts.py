bl_info = {
    "name": "Blender Tracts",
    "author": "Alexander S. Atalay",
    "version": (1, 0, 0),
    "blender": (4, 3, 0),
    "location": "View3D > Sidebar > Tool Tab",
    "description": "Visualize a sample of tractography streamlines (.tck/.txt)",
    "category": "Import-Export",
}

import bpy
import os
import sys
import subprocess
import json
import random

from bpy.props import StringProperty, IntProperty, FloatProperty
from bpy.types import Operator, Panel, PropertyGroup
from bpy_extras.io_utils import ImportHelper

def ensure_dependencies(report=None):
    try:
        import nibabel
        import numpy
    except ImportError:
        if report:
            report({'INFO'}, "Installing required packages...")
        subprocess.call([sys.executable, "-m", "ensurepip", "--user"])
        subprocess.call([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "--user"])
        subprocess.call([sys.executable, "-m", "pip", "install", "nibabel", "numpy", "--user"])
        from site import getusersitepackages
        sys.path.append(getusersitepackages())

class StreamlineSettings(PropertyGroup):
    def update_geometry_and_material(self, context):
        # Update radius value node in geometry node group
        geo_group = bpy.data.node_groups.get("streamline_geometry")
        if geo_group:
            for node in geo_group.nodes:
                if node.type == 'VALUE' and node.label == "StreamlineRadius":
                    node.outputs[0].default_value = self.radius

        # Update alpha value node in material
        mat = bpy.data.materials.get("streamlines")
        if mat and mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'VALUE' and node.label == "StreamlineAlpha":
                    node.outputs[0].default_value = self.alpha

    file_path: StringProperty(name="File Path", description="Path to .tck or .txt file", subtype='FILE_PATH')
    sample_count: IntProperty(name="Sample Count", default=15000, min=1)
    radius: FloatProperty(name="Streamline Radius", default=0.07, min=0.001, max=1.0, update=update_geometry_and_material)
    alpha: FloatProperty(name="Alpha", default=0.05, min=0.0, max=1.0, update=update_geometry_and_material)


def create_streamline_material():
    mat = bpy.data.materials.get("streamlines")
    if mat:
        return mat

    mat = bpy.data.materials.new(name="streamlines")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for node in nodes:
        nodes.remove(node)

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    alpha_input = nodes.new("ShaderNodeValue")
    alpha_input.label = "StreamlineAlpha"
    attr = nodes.new("ShaderNodeAttribute")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    abs_x = nodes.new("ShaderNodeMath")
    abs_y = nodes.new("ShaderNodeMath")
    abs_z = nodes.new("ShaderNodeMath")
    comb = nodes.new("ShaderNodeCombineColor")

    attr.attribute_name = "tangent"
    attr.attribute_type = 'GEOMETRY'

    abs_x.operation = abs_y.operation = abs_z.operation = 'ABSOLUTE'

    attr.location = (-600, 0)
    sep.location = (-400, 0)
    abs_x.location = (-200, 100)
    abs_y.location = (-200, 0)
    abs_z.location = (-200, -100)
    comb.location = (0, 0)
    bsdf.location = (200, 0)
    alpha_input.location = (-200, -300)
    output.location = (400, 0)

    alpha_input.outputs[0].default_value = 0.05

    links.new(attr.outputs['Vector'], sep.inputs['Vector'])
    links.new(sep.outputs['X'], abs_x.inputs[0])
    links.new(sep.outputs['Y'], abs_y.inputs[0])
    links.new(sep.outputs['Z'], abs_z.inputs[0])
    links.new(abs_x.outputs[0], comb.inputs['Red'])
    links.new(abs_y.outputs[0], comb.inputs['Green'])
    links.new(abs_z.outputs[0], comb.inputs['Blue'])
    links.new(alpha_input.outputs[0], bsdf.inputs['Alpha'])
    links.new(comb.outputs['Color'], bsdf.inputs['Emission Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    bsdf.inputs['Alpha'].default_value = 0.05
    bsdf.inputs['Emission Strength'].default_value = 1.0

    return mat

def create_streamline_geometry(radius):
    name = "streamline_geometry"

    if name in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[name], do_unlink=True)

    node_group = bpy.data.node_groups.new(name, 'GeometryNodeTree')

    # Add input/output sockets to the node group interface
    node_group.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    node_group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    # Create nodes
    group_input = node_group.nodes.new(type="NodeGroupInput")
    group_output = node_group.nodes.new(type="NodeGroupOutput")
    group_input.location = (-800, 0)
    group_output.location = (300, 0)

    tangent = node_group.nodes.new("GeometryNodeInputTangent")
    tangent.location = (-600, -200)

    store_attr = node_group.nodes.new("GeometryNodeStoreNamedAttribute")
    store_attr.location = (-400, 0)
    store_attr.inputs['Name'].default_value = "tangent"
    store_attr.data_type = 'FLOAT_VECTOR'
    store_attr.domain = 'POINT'

    circle = node_group.nodes.new("GeometryNodeCurvePrimitiveCircle")
    circle.inputs["Resolution"].default_value = 3
    circle.location = (-600, 200)

    value_node = node_group.nodes.new("ShaderNodeValue")
    value_node.outputs[0].default_value = radius
    value_node.label = "StreamlineRadius"
    value_node.location = (-800, 200)

    to_mesh = node_group.nodes.new("GeometryNodeCurveToMesh")
    to_mesh.location = (-200, 0)

    set_mat = node_group.nodes.new("GeometryNodeSetMaterial")
    set_mat.location = (100, 0)
    mat = create_streamline_material()
    set_mat.inputs['Material'].default_value = mat

    # Link nodes
    links = node_group.links
    links.new(group_input.outputs['Geometry'], store_attr.inputs['Geometry'])
    links.new(tangent.outputs['Tangent'], store_attr.inputs['Value'])
    links.new(store_attr.outputs['Geometry'], to_mesh.inputs['Curve'])
    links.new(circle.outputs['Curve'], to_mesh.inputs['Profile Curve'])
    links.new(to_mesh.outputs['Mesh'], set_mat.inputs['Geometry'])
    links.new(set_mat.outputs['Geometry'], group_output.inputs['Geometry'])

    # Connect the Value node to Circle's Radius
    links.new(value_node.outputs[0], circle.inputs["Radius"])

    return node_group

class ImportStreamlines(Operator):
    bl_idname = "import_streamlines.load"
    bl_label = "Import Streamlines"
    bl_description = "Load and display streamlines from .tck or .txt file"

    def execute(self, context):
        ensure_dependencies(self.report)
        from site import getusersitepackages
        if getusersitepackages() not in sys.path:
            sys.path.append(getusersitepackages())
        import numpy as np
        import nibabel as nib

        settings = context.scene.streamline_settings
        path = bpy.path.abspath(settings.file_path)
        ext = os.path.splitext(path)[1].lower()
        streamline_nodes = create_streamline_geometry(settings.radius)

        if ext == ".tck":
            raw_streamlines = nib.streamlines.load(path)
            all_streamlines = list(raw_streamlines.streamlines)
            if len(all_streamlines) > settings.sample_count:
                streamlines = random.sample(all_streamlines, settings.sample_count)
            else:
                self.report({'WARNING'}, f"Only {len(all_streamlines)} streamlines available in file.")
                streamlines = all_streamlines
            del raw_streamlines
        elif ext == ".txt":
            with open(path, 'r') as file:
                json_data = json.load(file)
            streamlines = [np.array(sl) for sl in json_data]
        else:
            self.report({'ERROR'}, "Unsupported file format. Use .tck or .txt.")
            return {'CANCELLED'}

        collection = bpy.data.collections.new("Streamlines")
        bpy.context.scene.collection.children.link(collection)

        for i, sl in enumerate(streamlines):
            curve = bpy.data.curves.new(name=f'streamline_{i}', type='CURVE')
            curve.dimensions = '3D'
            curve.resolution_u = 1
            spline = curve.splines.new('NURBS')
            spline.points.add(len(sl) - 1)
            for j, point in enumerate(sl):
                spline.points[j].co = list(point) + [1]
            obj = bpy.data.objects.new(f'streamline_{i}', curve)
            collection.objects.link(obj)
            mod = obj.modifiers.new(name="Streamline Geometry", type='NODES')
            mod.node_group = streamline_nodes


        mat = bpy.data.materials.get("streamlines")
        if mat and mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    node.inputs['Alpha'].default_value = settings.alpha

        if len(streamlines) > 20000:
            self.report({'WARNING'}, "Large streamline count may reduce performance.")
        return {'FINISHED'}

class BlenderTractsPanel(Panel):
    bl_label = "Blender Tracts"
    bl_idname = "BlenderTractsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.streamline_settings
        layout.prop(settings, "file_path")
        layout.prop(settings, "sample_count")
        layout.prop(settings, "radius")
        layout.prop(settings, "alpha")
        layout.operator("import_streamlines.load", text="Import Streamlines")

def register():
    bpy.utils.register_class(StreamlineSettings)
    bpy.types.Scene.streamline_settings = bpy.props.PointerProperty(type=StreamlineSettings)
    bpy.utils.register_class(IMPORT_OT_streamlines)
    bpy.utils.register_class(STREAMLINE_PT_panel)

def unregister():
    bpy.utils.unregister_class(BlenderTractsPanel)
    bpy.utils.unregister_class(ImportStreamlines)
    del bpy.types.Scene.streamline_settings
    bpy.utils.unregister_class(StreamlineSettings)

if __name__ == "__main__":
    register()