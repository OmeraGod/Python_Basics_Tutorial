import bpy
import math
import os
import random
from mathutils import Vector

OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'out'))
os.makedirs(OUT_DIR, exist_ok=True)

# ----------------------------
# Scene reset and render setup
# ----------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.materials, bpy.data.curves, bpy.data.meshes, bpy.data.cameras, bpy.data.lights):
    pass

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 240
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
scene.render.ffmpeg.audio_codec = 'NONE'
scene.render.filepath = os.path.join(OUT_DIR, 'solar_eclipse.mp4')
scene.render.image_settings.color_mode = 'RGB'

# Color management
scene.view_settings.look = 'AgX - Medium High Contrast'

# World
world = bpy.data.worlds.new('SpaceWorld') if not bpy.data.worlds else bpy.data.worlds[0]
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.001, 0.002, 0.006, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.05

# ----------------------------
# Helpers
# ----------------------------
def mat_principled(name, base, metallic=0.0, roughness=0.5, emission=None, emission_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*base, 1)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    if emission is not None:
        bsdf.inputs['Emission Color'].default_value = (*emission, 1)
        bsdf.inputs['Emission Strength'].default_value = emission_strength
    return m


def add_uv_sphere(name, loc, radius, segments=96, rings=64):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=radius, location=loc)
    obj = bpy.context.object
    obj.name = name
    bpy.ops.object.shade_smooth()
    return obj


def add_text(text, loc, size=0.7, extrude=0.02, align='CENTER'):
    bpy.ops.object.text_add(location=loc)
    t = bpy.context.object
    t.data.body = text
    t.data.align_x = align
    t.data.align_y = 'CENTER'
    t.data.size = size
    t.data.extrude = extrude
    t.data.bevel_depth = 0.005
    return t


def track_to(obj, target):
    c = obj.constraints.new(type='TRACK_TO')
    c.target = target
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    return c


def keyframe(obj, frame, location=None, scale=None):
    if location is not None:
        obj.location = location
        obj.keyframe_insert('location', frame=frame)
    if scale is not None:
        obj.scale = scale
        obj.keyframe_insert('scale', frame=frame)

# ----------------------------
# Sun
# ----------------------------
sun = add_uv_sphere('Sun', (0, 0, 0), 4.2)
sun_mat = mat_principled('SunMaterial', (1.0, 0.18, 0.01), roughness=0.3, emission=(1.0, 0.22, 0.01), emission_strength=8.0)
sun.data.materials.append(sun_mat)

# Sun procedural variation
nt = sun_mat.node_tree
bsdf = nt.nodes.get('Principled BSDF')
noise = nt.nodes.new('ShaderNodeTexNoise')
noise.inputs['Scale'].default_value = 3.2
noise.inputs['Detail'].default_value = 5.0
noise.inputs['Roughness'].default_value = 0.7
ramp = nt.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (0.7, 0.01, 0.0, 1)
ramp.color_ramp.elements[1].color = (1.0, 0.65, 0.02, 1)
nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
nt.links.new(ramp.outputs['Color'], bsdf.inputs['Emission Color'])

# Corona rings
for r, alpha in [(5.0, 0.16), (5.8, 0.07), (6.6, 0.03)]:
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.07, major_segments=160, minor_segments=12, location=(0, 0, 0), rotation=(math.radians(90),0,0))
    ring = bpy.context.object
    ring.name = f'Corona_{r}'
    m = bpy.data.materials.new(f'CoronaMat_{r}')
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (1.0, 0.35, 0.03, 1)
    bs.inputs['Emission Color'].default_value = (1.0, 0.25, 0.02, 1)
    bs.inputs['Emission Strength'].default_value = 6.0
    bs.inputs['Alpha'].default_value = alpha
    m.surface_render_method = 'DITHERED'
    ring.data.materials.append(m)

# Sun point light
bpy.ops.object.light_add(type='POINT', location=(0, 0, 0))
sl = bpy.context.object
sl.name = 'SunLight'
sl.data.energy = 11000
sl.data.color = (1.0, 0.58, 0.24)
sl.data.shadow_soft_size = 4.2

# ----------------------------
# Earth
# ----------------------------
earth = add_uv_sphere('Earth', (28, 0, 0), 2.25)
earth_mat = bpy.data.materials.new('EarthMaterial')
earth_mat.use_nodes = True
ent = earth_mat.node_tree
bsdf = ent.nodes.get('Principled BSDF')
bsdf.inputs['Roughness'].default_value = 0.72
noise = ent.nodes.new('ShaderNodeTexNoise')
noise.inputs['Scale'].default_value = 2.0
noise.inputs['Detail'].default_value = 5.0
noise.inputs['Roughness'].default_value = 0.65
ramp = ent.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position = 0.40
ramp.color_ramp.elements[0].color = (0.005, 0.03, 0.18, 1)
ramp.color_ramp.elements[1].position = 0.59
ramp.color_ramp.elements[1].color = (0.04, 0.34, 0.04, 1)
# Add sandy midtone
ramp.color_ramp.elements.new(0.52).color = (0.25, 0.16, 0.035, 1)
ent.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
ent.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
# Bump
bump = ent.nodes.new('ShaderNodeBump')
bump.inputs['Strength'].default_value = 0.18
bump.inputs['Distance'].default_value = 0.12
ent.links.new(noise.outputs['Fac'], bump.inputs['Height'])
ent.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
earth.data.materials.append(earth_mat)

# Atmosphere shell
atmo = add_uv_sphere('Atmosphere', (28, 0, 0), 2.34)
atmo_mat = bpy.data.materials.new('AtmosphereMaterial')
atmo_mat.use_nodes = True
absdf = atmo_mat.node_tree.nodes.get('Principled BSDF')
absdf.inputs['Base Color'].default_value = (0.01, 0.16, 0.85, 1)
absdf.inputs['Emission Color'].default_value = (0.01, 0.08, 0.6, 1)
absdf.inputs['Emission Strength'].default_value = 0.5
absdf.inputs['Alpha'].default_value = 0.17
absdf.inputs['Roughness'].default_value = 0.25
atmo_mat.surface_render_method = 'DITHERED'
atmo.data.materials.append(atmo_mat)

# ----------------------------
# Moon and eclipse motion
# ----------------------------
moon = add_uv_sphere('Moon', (17.0, -5.5, 0), 0.8, segments=72, rings=48)
moon_mat = bpy.data.materials.new('MoonMaterial')
moon_mat.use_nodes = True
mnt = moon_mat.node_tree
mbsdf = mnt.nodes.get('Principled BSDF')
mbsdf.inputs['Base Color'].default_value = (0.10, 0.105, 0.12, 1)
mbsdf.inputs['Roughness'].default_value = 0.92
mnoise = mnt.nodes.new('ShaderNodeTexNoise')
mnoise.inputs['Scale'].default_value = 7.5
mnoise.inputs['Detail'].default_value = 3.5
mbump = mnt.nodes.new('ShaderNodeBump')
mbump.inputs['Strength'].default_value = 0.4
mbump.inputs['Distance'].default_value = 0.12
mnt.links.new(mnoise.outputs['Fac'], mbump.inputs['Height'])
mnt.links.new(mbump.outputs['Normal'], mbsdf.inputs['Normal'])
moon.data.materials.append(moon_mat)

# Moon crosses the Sun-Earth line
keyframe(moon, 1, (17.0, -5.5, 0.3))
keyframe(moon, 92, (17.0, -1.4, 0.08))
keyframe(moon, 120, (17.0, 0.0, 0.0))
keyframe(moon, 148, (17.0, 1.4, -0.08))
keyframe(moon, 240, (17.0, 5.5, -0.3))
# Smooth interpolation
if moon.animation_data and moon.animation_data.action:
    for fc in moon.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'

# ----------------------------
# Shadow cones (educational visualization)
# ----------------------------
def add_cone_between(name, x1, x2, r1, r2, color, alpha):
    length = x2 - x1
    mid = (x1+x2)/2
    bpy.ops.mesh.primitive_cone_add(vertices=96, radius1=r1, radius2=r2, depth=length, location=(mid,0,0), rotation=(0,math.radians(90),0))
    obj = bpy.context.object
    obj.name = name
    m = bpy.data.materials.new(name+'Mat')
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color,1)
    bs.inputs['Alpha'].default_value = alpha
    bs.inputs['Roughness'].default_value = 1.0
    m.surface_render_method = 'DITHERED'
    obj.data.materials.append(m)
    return obj

umbra = add_cone_between('Umbra', 17.6, 27.3, 0.50, 0.10, (0.01,0.01,0.015), 0.60)
penumbra = add_cone_between('Penumbra', 17.2, 28.1, 0.92, 2.1, (0.12,0.07,0.02), 0.10)
# Hide cones early, show around eclipse
for obj in (umbra, penumbra):
    obj.scale = (1, 0.001, 0.001)
    obj.keyframe_insert('scale', frame=1)
    obj.keyframe_insert('scale', frame=76)
    obj.scale = (1,1,1)
    obj.keyframe_insert('scale', frame=96)
    obj.keyframe_insert('scale', frame=145)
    obj.scale = (1,0.001,0.001)
    obj.keyframe_insert('scale', frame=166)

# ----------------------------
# Orbit guides
# ----------------------------
for x, radius in [(17,5.6), (28,0.0)]:
    if radius > 0:
        bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=0.015, major_segments=180, minor_segments=8, location=(x,0,0), rotation=(0,math.radians(90),0))
        tor = bpy.context.object
        tor.name = 'MoonOrbitGuide'
        gm = mat_principled('GuideMaterial', (0.12,0.22,0.4), roughness=0.8, emission=(0.03,0.06,0.14), emission_strength=1.5)
        tor.data.materials.append(gm)

# ----------------------------
# Star field
# ----------------------------
random.seed(7)
star_mat = mat_principled('StarMat', (1,1,1), roughness=0.2, emission=(1,1,1), emission_strength=3.5)
for i in range(110):
    x = random.uniform(-10, 40)
    y = random.uniform(8, 22) * random.choice((-1,1))
    z = random.uniform(-12, 16)
    s = random.uniform(0.025, 0.08)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=s, location=(x,y,z))
    st = bpy.context.object
    st.name = f'Star_{i:03d}'
    st.data.materials.append(star_mat)

# ----------------------------
# Camera and animated target
# ----------------------------
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(14,0,0))
target = bpy.context.object
target.name = 'CameraTarget'

bpy.ops.object.camera_add(location=(14,-34,11))
cam = bpy.context.object
cam.name = 'Camera'
scene.camera = cam
cam.data.lens = 47
cam.data.sensor_width = 36
track_to(cam, target)

# Wide view -> tighter alignment -> Earth side
keyframe(cam, 1, (14,-34,11))
keyframe(target, 1, (14,0,0))
keyframe(cam, 72, (13,-28,8.5))
keyframe(target, 72, (14,0,0))
keyframe(cam, 118, (15,-24,5.5))
keyframe(target, 118, (16,0,0))
keyframe(cam, 160, (21,-19,4.0))
keyframe(target, 160, (22.5,0,0))
keyframe(cam, 240, (14,-31,9.0))
keyframe(target, 240, (14,0,0))

# ----------------------------
# Titles and labels facing camera
# ----------------------------
text_mat = mat_principled('TextMaterial', (0.93,0.95,1.0), roughness=0.4, emission=(0.18,0.22,0.35), emission_strength=1.2)
accent_mat = mat_principled('AccentTextMaterial', (1.0,0.48,0.08), roughness=0.35, emission=(0.9,0.18,0.02), emission_strength=2.4)

# Text arranged on a plane roughly facing camera at opening shot
texts = []
for label, loc, size, mat in [
    ('MẶT TRỜI', (0,-5.1,5.1), 0.55, accent_mat),
    ('MẶT TRĂNG', (17,-4.2,2.1), 0.42, text_mat),
    ('TRÁI ĐẤT', (28,-4.0,3.2), 0.48, text_mat),
]:
    t = add_text(label, loc, size=size)
    t.rotation_euler = (math.radians(68), 0, 0)
    t.data.materials.append(mat)
    texts.append(t)

# Main title near top in wide shot
main_title = add_text('HIỆN TƯỢNG NHẬT THỰ', (14,-7.0,9.5), size=0.82)
main_title.rotation_euler = (math.radians(70), 0, 0)
main_title.data.materials.append(text_mat)

# ----------------------------
# Eclipse marker on Earth
# ----------------------------
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=32, radius=0.18, location=(25.82,0,0))
marker = bpy.context.object
marker.name = 'TotalitySpot'
mark_mat = mat_principled('MarkerMat', (0.9,0.04,0.01), roughness=0.2, emission=(1.0,0.02,0.0), emission_strength=4.5)
marker.data.materials.append(mark_mat)
marker.scale=(0.1,0.1,0.1); marker.keyframe_insert('scale', frame=1)
marker.keyframe_insert('scale', frame=96)
marker.scale=(1,1,1); marker.keyframe_insert('scale', frame=116)
marker.keyframe_insert('scale', frame=144)
marker.scale=(0.1,0.1,0.1); marker.keyframe_insert('scale', frame=165)

# ----------------------------
# Compositor bloom/glare
# ----------------------------
scene.use_nodes = True
nodes = scene.node_tree.nodes
links = scene.node_tree.links
nodes.clear()
rl = nodes.new('CompositorNodeRLayers')
gl = nodes.new('CompositorNodeGlare')
gl.glare_type = 'FOG_GLOW'
gl.quality = 'HIGH'
gl.threshold = 1.0
gl.size = 7
comp = nodes.new('CompositorNodeComposite')
links.new(rl.outputs['Image'], gl.inputs['Image'])
links.new(gl.outputs['Image'], comp.inputs['Image'])

# ----------------------------
# Save .blend and render
# ----------------------------
blend_path = os.path.join(OUT_DIR, 'solar_eclipse.blend')
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print('Saved blend:', blend_path)
print('Rendering animation to:', scene.render.filepath)
bpy.ops.render.render(animation=True)
print('DONE')
