import bpy
import math
import os
import random
from mathutils import Vector

FPS = 24
END = 144  # 6 seconds
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'out4k'))
FRAMES = os.path.join(OUT, 'frames')
os.makedirs(FRAMES, exist_ok=True)

# ---------- helpers ----------
def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def mat_principled(name, base, emission=None, strength=0.0, rough=0.5, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*base, 1.0)
    b.inputs['Roughness'].default_value = rough
    if emission is not None:
        if 'Emission Color' in b.inputs:
            b.inputs['Emission Color'].default_value = (*emission, 1.0)
            b.inputs['Emission Strength'].default_value = strength
        else:
            b.inputs['Emission'].default_value = (*emission, 1.0)
            b.inputs['Emission Strength'].default_value = strength
    b.inputs['Alpha'].default_value = alpha
    try:
        m.blend_method = 'BLEND' if alpha < 1.0 else 'OPAQUE'
        m.shadow_method = 'HASHED'
    except Exception:
        pass
    return m


def add_sphere(name, loc, radius, mat, seg=128, rings=64):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=radius, location=loc)
    o = bpy.context.object
    o.name = name
    bpy.ops.object.shade_smooth()
    o.data.materials.append(mat)
    return o


def k_loc(o, f, loc):
    o.location = loc
    o.keyframe_insert('location', frame=f)


def key_hidden(o, f, hidden):
    o.hide_render = hidden
    o.hide_viewport = hidden
    o.keyframe_insert('hide_render', frame=f)
    o.keyframe_insert('hide_viewport', frame=f)


def smooth(o):
    if o.animation_data and o.animation_data.action:
        for fc in o.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                if fc.data_path in {'hide_render', 'hide_viewport'}:
                    kp.interpolation = 'CONSTANT'
                else:
                    kp.interpolation = 'BEZIER'


clear_scene()
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = END
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 3840
scene.render.resolution_y = 2160
scene.render.resolution_percentage = 100
scene.render.fps = FPS
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.color_depth = '8'
scene.render.filepath = os.path.join(FRAMES, 'frame_')
scene.render.film_transparent = False
try:
    scene.eevee.taa_render_samples = 32
    scene.eevee.use_bloom = False
except Exception:
    pass
try:
    scene.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass

# world: daytime blue -> dark totality -> blue
world = bpy.data.worlds.new('SkyWorld') if not bpy.data.worlds else bpy.data.worlds[0]
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes['Background']
bg.inputs['Color'].default_value = (0.010, 0.045, 0.16, 1.0)
for f, s in [(1,0.20),(45,0.16),(63,0.055),(70,0.018),(78,0.018),(87,0.055),(102,0.16),(END,0.20)]:
    bg.inputs['Strength'].default_value = s
    bg.inputs['Strength'].keyframe_insert('default_value', frame=f)

# camera: telephoto fixed composition, tiny drift
bpy.ops.object.camera_add(location=(0.0,-40.0,0.05))
cam = bpy.context.object
scene.camera = cam
cam.data.lens = 180
cam.data.sensor_width = 36
look_at(cam, (0,0,0))
k_loc(cam,1,(0.00,-40.0,0.05))
k_loc(cam,72,(0.025,-39.7,0.03))
k_loc(cam,END,(-0.02,-40.0,0.055))
smooth(cam)
if cam.animation_data and cam.animation_data.action:
    for fc in cam.animation_data.action.fcurves:
        if fc.data_path == 'location':
            n = fc.modifiers.new(type='NOISE')
            n.strength = 0.004
            n.scale = 28.0

# Sun
sun_mat = mat_principled('SunMat',(1.0,0.78,0.22), emission=(1.0,0.78,0.25), strength=10.0, rough=0.25)
sun = add_sphere('Sun',(0,0,0),2.0,sun_mat,160,96)
# subtle surface texture
nt = sun_mat.node_tree
bs = nt.nodes['Principled BSDF']
tex = nt.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value=9.0; tex.inputs['Detail'].default_value=5.0; tex.inputs['Roughness'].default_value=0.65
ramp = nt.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color=(1.0,0.34,0.04,1)
ramp.color_ramp.elements[1].color=(1.0,0.95,0.45,1)
nt.links.new(tex.outputs['Fac'],ramp.inputs['Fac'])
nt.links.new(ramp.outputs['Color'],bs.inputs['Base Color'])
if 'Emission Color' in bs.inputs:
    nt.links.new(ramp.outputs['Color'],bs.inputs['Emission Color'])

# Corona as emissive torus layers in plane facing camera
for i,(rad,minor,st,alpha) in enumerate([(2.22,0.065,8.0,0.75),(2.38,0.045,5.5,0.45),(2.58,0.030,3.0,0.25)]):
    bpy.ops.mesh.primitive_torus_add(major_radius=rad, minor_radius=minor, major_segments=160, minor_segments=16, location=(0,-0.06,0), rotation=(math.radians(90),0,0))
    ring=bpy.context.object; ring.name=f'Corona_{i}'
    m=mat_principled(f'CoronaMat_{i}',(1.0,0.92,0.78),emission=(1.0,0.94,0.84),strength=st,rough=0.2,alpha=alpha)
    ring.data.materials.append(m)

# A faint large halo disk to create natural glow
halo = add_sphere('Halo',(0,0.10,0),2.72,mat_principled('HaloMat',(0.95,0.78,0.35),emission=(1.0,0.82,0.38),strength=0.8,rough=0.2,alpha=0.035),128,64)

# Moon silhouette: apparent size ~ Sun, closer to camera
moon_mat = mat_principled('MoonMat',(0.006,0.007,0.009),rough=0.92)
moon = add_sphere('Moon',(-2.95,-18.0,0.16),1.12,moon_mat,144,80)
# texture/bump although mostly silhouette
mnt=moon_mat.node_tree; mbs=mnt.nodes['Principled BSDF']; mn=mnt.nodes.new('ShaderNodeTexNoise'); mn.inputs['Scale'].default_value=18.0; mn.inputs['Detail'].default_value=4.0
bump=mnt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=0.22; bump.inputs['Distance'].default_value=0.08
mnt.links.new(mn.outputs['Fac'],bump.inputs['Height']); mnt.links.new(bump.outputs['Normal'],mbs.inputs['Normal'])

# transit; totality centered around frame 72
for f,loc in [(1,(-2.95,-18.0,0.18)),(38,(-1.72,-18.0,0.12)),(58,(-0.72,-18.0,0.06)),(68,(-0.20,-18.0,0.02)),(72,(0.00,-18.0,0.00)),(76,(0.20,-18.0,-0.02)),(86,(0.72,-18.0,-0.05)),(106,(1.72,-18.0,-0.10)),(END,(2.95,-18.0,-0.18))]:
    k_loc(moon,f,loc)
smooth(moon)

# Diamond ring beads, shown briefly around totality contacts
bead_mat = mat_principled('BeadMat',(1,1,0.9),emission=(1,0.96,0.8),strength=35.0,rough=0.1)
bead_r = add_sphere('DiamondRight',(2.02,-0.22,0.0),0.075,bead_mat,48,24)
bead_l = add_sphere('DiamondLeft',(-2.02,-0.22,0.0),0.075,bead_mat,48,24)
for obj, window in [(bead_r,(61,68)),(bead_l,(76,83))]:
    key_hidden(obj,1,True)
    key_hidden(obj,window[0]-1,True)
    key_hidden(obj,window[0],False)
    key_hidden(obj,window[1],False)
    key_hidden(obj,window[1]+1,True)
    key_hidden(obj,END,True)
    smooth(obj)

# Stars visible only around totality
random.seed(18)
star_mat=mat_principled('StarMat',(1,1,1),emission=(1,1,1),strength=5.0,rough=0.1)
for i in range(36):
    # behind sun, within narrow camera field
    st=add_sphere(f'Star_{i:02d}',(random.uniform(-4.2,4.2),3.5,random.uniform(-2.3,2.3)),random.uniform(0.012,0.030),star_mat,16,8)
    key_hidden(st,1,True); key_hidden(st,60,True); key_hidden(st,61,False); key_hidden(st,88,False); key_hidden(st,89,True); key_hidden(st,END,True)
    smooth(st)

# subtle atmospheric haze veil around sun
bpy.ops.mesh.primitive_plane_add(size=18, location=(0,-8.0,0), rotation=(math.radians(90),0,0))
haze=bpy.context.object
haze.name='HazeVeil'
hm=bpy.data.materials.new('HazeMat'); hm.use_nodes=True
hbs=hm.node_tree.nodes['Principled BSDF']; hbs.inputs['Base Color'].default_value=(0.08,0.15,0.30,1); hbs.inputs['Roughness'].default_value=1.0; hbs.inputs['Alpha'].default_value=0.035
try:
    hm.blend_method='BLEND'; hm.shadow_method='NONE'
except Exception: pass
haze.data.materials.append(hm)

# compositor glow and subtle lens distortion
scene.use_nodes=True
cn=scene.node_tree
for n in list(cn.nodes): cn.nodes.remove(n)
rl=cn.nodes.new('CompositorNodeRLayers')
gl=cn.nodes.new('CompositorNodeGlare'); gl.glare_type='FOG_GLOW'; gl.quality='HIGH'; gl.threshold=0.75; gl.size=7
lens=cn.nodes.new('CompositorNodeLensdist'); lens.inputs['Distort'].default_value=0.003
comp=cn.nodes.new('CompositorNodeComposite')
cn.links.new(rl.outputs['Image'],gl.inputs['Image']); cn.links.new(gl.outputs['Image'],lens.inputs['Image']); cn.links.new(lens.outputs['Image'],comp.inputs['Image'])

# Save blend for debug, then render PNG sequence
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'solar_eclipse_4k.blend'))
print('Rendering 4K frames to', FRAMES)
bpy.ops.render.render(animation=True)
print('BLENDER_RENDER_DONE')
