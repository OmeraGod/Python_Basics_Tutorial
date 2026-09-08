import bpy
import math
import os
import random

OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'out'))
os.makedirs(OUT_DIR, exist_ok=True)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 240
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
scene.render.ffmpeg.audio_codec = 'NONE'
scene.render.filepath = os.path.join(OUT_DIR, 'solar_eclipse.mp4')
scene.render.image_settings.color_mode = 'RGB'
try:
    scene.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass

world = bpy.data.worlds.new('SpaceWorld') if not bpy.data.worlds else bpy.data.worlds[0]
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.001, 0.002, 0.006, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.03


def set_alpha_material(mat, alpha):
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Alpha'].default_value = alpha
    try:
        mat.blend_method = 'BLEND'
        mat.use_screen_refraction = True
    except Exception:
        pass


def mat_principled(name, base, roughness=0.5, emission=None, emission_strength=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*base, 1)
    bsdf.inputs['Roughness'].default_value = roughness
    if emission is not None:
        bsdf.inputs['Emission Color'].default_value = (*emission, 1)
        bsdf.inputs['Emission Strength'].default_value = emission_strength
    if alpha < 1.0:
        set_alpha_material(m, alpha)
    return m


def add_uv_sphere(name, loc, radius, segments=80, rings=48):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=radius, location=loc)
    obj = bpy.context.object
    obj.name = name
    bpy.ops.object.shade_smooth()
    return obj


def keyframe(obj, frame, location=None, scale=None):
    if location is not None:
        obj.location = location
        obj.keyframe_insert(data_path='location', frame=frame)
    if scale is not None:
        obj.scale = scale
        obj.keyframe_insert(data_path='scale', frame=frame)


def track_to(obj, target):
    c = obj.constraints.new(type='TRACK_TO')
    c.target = target
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'

# SUN
sun = add_uv_sphere('Sun', (0,0,0), 4.2)
sun_mat = mat_principled('SunMaterial', (1.0,0.16,0.01), 0.3, (1.0,0.19,0.01), 7.0)
sun.data.materials.append(sun_mat)
nt = sun_mat.node_tree
bsdf = nt.nodes.get('Principled BSDF')
noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=3.1; noise.inputs['Detail'].default_value=4.0
ramp = nt.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color=(0.45,0.005,0.0,1)
ramp.color_ramp.elements[1].color=(1.0,0.52,0.01,1)
nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
nt.links.new(ramp.outputs['Color'], bsdf.inputs['Emission Color'])

for r, a in [(4.9,0.18),(5.6,0.09),(6.3,0.035)]:
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.06, major_segments=128, minor_segments=12, location=(0,0,0), rotation=(math.radians(90),0,0))
    ring=bpy.context.object
    ring.data.materials.append(mat_principled(f'Corona{r}', (1.0,0.35,0.02), 0.4, (1.0,0.22,0.01), 5.0, a))

bpy.ops.object.light_add(type='POINT', location=(0,0,0))
light=bpy.context.object
light.data.energy=9000
light.data.color=(1.0,0.58,0.28)
light.data.shadow_soft_size=4.2

# EARTH
earth=add_uv_sphere('Earth',(28,0,0),2.25)
em=bpy.data.materials.new('EarthMaterial'); em.use_nodes=True
ent=em.node_tree; ebs=ent.nodes.get('Principled BSDF'); ebs.inputs['Roughness'].default_value=0.72
en=ent.nodes.new('ShaderNodeTexNoise'); en.inputs['Scale'].default_value=2.2; en.inputs['Detail'].default_value=5.0
er=ent.nodes.new('ShaderNodeValToRGB')
er.color_ramp.elements[0].position=0.40; er.color_ramp.elements[0].color=(0.002,0.02,0.16,1)
er.color_ramp.elements[1].position=0.61; er.color_ramp.elements[1].color=(0.03,0.34,0.035,1)
er.color_ramp.elements.new(0.51).color=(0.30,0.18,0.045,1)
ent.links.new(en.outputs['Fac'], er.inputs['Fac']); ent.links.new(er.outputs['Color'], ebs.inputs['Base Color'])
eb=ent.nodes.new('ShaderNodeBump'); eb.inputs['Strength'].default_value=0.2; ent.links.new(en.outputs['Fac'], eb.inputs['Height']); ent.links.new(eb.outputs['Normal'], ebs.inputs['Normal'])
earth.data.materials.append(em)

atmo=add_uv_sphere('Atmosphere',(28,0,0),2.34)
atmo.data.materials.append(mat_principled('AtmosphereMaterial',(0.01,0.12,0.8),0.25,(0.01,0.08,0.65),0.5,0.14))

# MOON
moon=add_uv_sphere('Moon',(17,-5.5,0.3),0.82,64,40)
mm=bpy.data.materials.new('MoonMaterial'); mm.use_nodes=True
mnt=mm.node_tree; mbs=mnt.nodes.get('Principled BSDF'); mbs.inputs['Base Color'].default_value=(0.085,0.09,0.105,1); mbs.inputs['Roughness'].default_value=0.95
mn=mnt.nodes.new('ShaderNodeTexNoise'); mn.inputs['Scale'].default_value=7.5; mn.inputs['Detail'].default_value=3.0
mb=mnt.nodes.new('ShaderNodeBump'); mb.inputs['Strength'].default_value=0.45; mnt.links.new(mn.outputs['Fac'],mb.inputs['Height']); mnt.links.new(mb.outputs['Normal'],mbs.inputs['Normal'])
moon.data.materials.append(mm)
for f,loc in [(1,(17,-5.5,0.3)),(92,(17,-1.4,0.08)),(120,(17,0,0)),(148,(17,1.4,-0.08)),(240,(17,5.5,-0.3))]: keyframe(moon,f,loc)

# SHADOW CONES
def cone(name,x1,x2,r1,r2,color,alpha):
    length=x2-x1; mid=(x1+x2)/2
    bpy.ops.mesh.primitive_cone_add(vertices=64,radius1=r1,radius2=r2,depth=length,location=(mid,0,0),rotation=(0,math.radians(90),0))
    o=bpy.context.object; o.name=name; o.data.materials.append(mat_principled(name+'Mat',color,1.0,None,0,alpha)); return o
umbra=cone('Umbra',17.6,27.3,0.5,0.1,(0.01,0.01,0.015),0.58)
pen=cone('Penumbra',17.2,28.1,0.92,2.05,(0.15,0.07,0.015),0.08)
for o in (umbra,pen):
    for f,s in [(1,(1,0.001,0.001)),(76,(1,0.001,0.001)),(96,(1,1,1)),(145,(1,1,1)),(166,(1,0.001,0.001))]: keyframe(o,f,scale=s)

# STARS
random.seed(7)
sm=mat_principled('StarMat',(1,1,1),0.2,(1,1,1),3.0)
for i in range(90):
    p=(random.uniform(-8,38),random.uniform(8,20)*random.choice((-1,1)),random.uniform(-10,14))
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=random.uniform(0.025,0.065),location=p)
    bpy.context.object.data.materials.append(sm)

# CAMERA
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(14,0,0)); target=bpy.context.object
bpy.ops.object.camera_add(location=(14,-34,11)); cam=bpy.context.object; scene.camera=cam; cam.data.lens=47; track_to(cam,target)
for f,cl,tl in [(1,(14,-34,11),(14,0,0)),(72,(13,-28,8.5),(14,0,0)),(118,(15,-24,5.5),(16,0,0)),(160,(21,-19,4.0),(22.5,0,0)),(240,(14,-31,9),(14,0,0))]:
    keyframe(cam,f,cl); keyframe(target,f,tl)

# LABELS
textmat=mat_principled('TextMat',(0.92,0.95,1),0.4,(0.2,0.24,0.35),1.3)
accent=mat_principled('AccentMat',(1.0,0.45,0.05),0.35,(0.9,0.15,0.01),2.0)
def add_text(body,loc,size,mat):
    bpy.ops.object.text_add(location=loc)
    t=bpy.context.object; t.data.body=body; t.data.align_x='CENTER'; t.data.align_y='CENTER'; t.data.size=size; t.data.extrude=0.018; t.rotation_euler=(math.radians(70),0,0); t.data.materials.append(mat)
add_text('HIỆN TƯỢNG NHẬT THỰ',(14,-7.0,9.5),0.82,textmat)
add_text('MẶT TRỜI',(0,-5.0,5.0),0.52,accent)
add_text('MẶT TRĂNG',(17,-4.1,2.0),0.42,textmat)
add_text('TRÁI ĐẤT',(28,-4.0,3.1),0.48,textmat)

# TOTALITY MARKER
mark=add_uv_sphere('TotalitySpot',(25.82,0,0),0.18,40,24)
mark.data.materials.append(mat_principled('MarkerMat',(0.8,0.01,0.005),0.2,(1,0.01,0),4.0))
for f,s in [(1,(0.1,0.1,0.1)),(96,(0.1,0.1,0.1)),(116,(1,1,1)),(144,(1,1,1)),(165,(0.1,0.1,0.1))]: keyframe(mark,f,scale=s)

# COMPOSITOR GLOW
scene.use_nodes=True
nodes=scene.node_tree.nodes; links=scene.node_tree.links; nodes.clear()
rl=nodes.new('CompositorNodeRLayers'); gl=nodes.new('CompositorNodeGlare'); gl.glare_type='FOG_GLOW'; gl.quality='HIGH'; gl.threshold=1.0; gl.size=7
co=nodes.new('CompositorNodeComposite'); links.new(rl.outputs['Image'],gl.inputs['Image']); links.new(gl.outputs['Image'],co.inputs['Image'])

blend_path=os.path.join(OUT_DIR,'solar_eclipse.blend')
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print('Saved',blend_path)
bpy.ops.render.render(animation=True)
print('DONE',scene.render.filepath)
