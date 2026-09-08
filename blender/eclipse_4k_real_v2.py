import bpy, math, os, random
from mathutils import Vector

FPS=24
END=144
OUT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','out4kv2'))
FRAMES=os.path.join(OUT,'frames')
os.makedirs(FRAMES,exist_ok=True)

def clear():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

def look_at(obj,target=(0,0,0)):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def pmat(name,base,em=None,st=0,rough=.5,alpha=1.0):
    m=bpy.data.materials.new(name); m.use_nodes=True
    b=m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value=(*base,1); b.inputs['Roughness'].default_value=rough
    if em is not None:
        if 'Emission Color' in b.inputs:
            b.inputs['Emission Color'].default_value=(*em,1); b.inputs['Emission Strength'].default_value=st
        else:
            b.inputs['Emission'].default_value=(*em,1); b.inputs['Emission Strength'].default_value=st
    b.inputs['Alpha'].default_value=alpha
    try:
        m.blend_method='BLEND' if alpha<1 else 'OPAQUE'; m.shadow_method='HASHED'
    except: pass
    return m

def sphere(name,loc,r,mat,seg=128,rings=64):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,radius=r,location=loc)
    o=bpy.context.object; o.name=name; bpy.ops.object.shade_smooth(); o.data.materials.append(mat); return o

def kloc(o,f,loc):
    o.location=loc; o.keyframe_insert('location',frame=f)

def khide(o,f,v):
    o.hide_render=v; o.hide_viewport=v; o.keyframe_insert('hide_render',frame=f); o.keyframe_insert('hide_viewport',frame=f)

def smooth(o):
    if o.animation_data and o.animation_data.action:
        for fc in o.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation='CONSTANT' if fc.data_path in {'hide_render','hide_viewport'} else 'BEZIER'

def corona_plane(name,size,y,inner0,peak,fade1,outer,em_strength,noise_scale,stretch=(1,1,1)):
    bpy.ops.mesh.primitive_plane_add(size=size,location=(0,y,0),rotation=(math.radians(90),0,0))
    o=bpy.context.object; o.name=name; o.scale=stretch
    m=bpy.data.materials.new(name+'Mat'); m.use_nodes=True
    try: m.blend_method='BLEND'; m.shadow_method='NONE'
    except: pass
    nt=m.node_tree; nt.nodes.clear()
    out=nt.nodes.new('ShaderNodeOutputMaterial')
    trans=nt.nodes.new('ShaderNodeBsdfTransparent')
    emis=nt.nodes.new('ShaderNodeEmission'); emis.inputs['Color'].default_value=(1.0,.96,.88,1); emis.inputs['Strength'].default_value=em_strength
    tc=nt.nodes.new('ShaderNodeTexCoord')
    dist=nt.nodes.new('ShaderNodeVectorMath'); dist.operation='DISTANCE'; dist.inputs[1].default_value=(.5,.5,0)
    ramp=nt.nodes.new('ShaderNodeValToRGB')
    cr=ramp.color_ramp; cr.interpolation='EASE'
    cr.elements.remove(cr.elements[1]); e0=cr.elements[0]; e0.position=inner0; e0.color=(0,0,0,1)
    e1=cr.elements.new(peak); e1.color=(1,1,1,1)
    e2=cr.elements.new(fade1); e2.color=(.34,.34,.34,1)
    e3=cr.elements.new(outer); e3.color=(0,0,0,1)
    noise=nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=noise_scale; noise.inputs['Detail'].default_value=5; noise.inputs['Roughness'].default_value=.75
    mul=nt.nodes.new('ShaderNodeMath'); mul.operation='MULTIPLY'; mul.inputs[1].default_value=.35
    add=nt.nodes.new('ShaderNodeMath'); add.operation='ADD'; add.inputs[1].default_value=.72
    facmul=nt.nodes.new('ShaderNodeMath'); facmul.operation='MULTIPLY'
    mix=nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(tc.outputs['Generated'],dist.inputs[0]); nt.links.new(dist.outputs['Value'],ramp.inputs['Fac'])
    nt.links.new(tc.outputs['Generated'],noise.inputs['Vector']); nt.links.new(noise.outputs['Fac'],mul.inputs[0]); nt.links.new(mul.outputs[0],add.inputs[0])
    nt.links.new(ramp.outputs['Color'],facmul.inputs[0]); nt.links.new(add.outputs[0],facmul.inputs[1])
    nt.links.new(facmul.outputs[0],mix.inputs[0]); nt.links.new(trans.outputs[0],mix.inputs[1]); nt.links.new(emis.outputs[0],mix.inputs[2]); nt.links.new(mix.outputs[0],out.inputs['Surface'])
    for f,val in [(1,em_strength*.18),(48,em_strength*.22),(62,em_strength*.65),(69,em_strength*1.25),(72,em_strength*1.45),(78,em_strength*1.25),(88,em_strength*.55),(104,em_strength*.22),(END,em_strength*.18)]:
        emis.inputs['Strength'].default_value=val; emis.inputs['Strength'].keyframe_insert('default_value',frame=f)
    return o

clear(); scene=bpy.context.scene
scene.frame_start=1; scene.frame_end=END; scene.render.engine='BLENDER_EEVEE'; scene.render.resolution_x=3840; scene.render.resolution_y=2160; scene.render.resolution_percentage=100; scene.render.fps=FPS
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'; scene.render.filepath=os.path.join(FRAMES,'frame_')
try: scene.eevee.taa_render_samples=48
except: pass
try: scene.view_settings.look='AgX - Medium High Contrast'
except: pass

world=bpy.data.worlds[0] if bpy.data.worlds else bpy.data.worlds.new('Sky'); scene.world=world; world.use_nodes=True
bg=world.node_tree.nodes['Background']; bg.inputs['Color'].default_value=(.008,.035,.12,1)
for f,s in [(1,.22),(42,.19),(58,.10),(66,.035),(70,.012),(80,.012),(88,.045),(104,.15),(END,.22)]:
    bg.inputs['Strength'].default_value=s; bg.inputs['Strength'].keyframe_insert('default_value',frame=f)

bpy.ops.object.camera_add(location=(0,-40,.04)); cam=bpy.context.object; scene.camera=cam; cam.data.lens=155; cam.data.sensor_width=36; look_at(cam)
for f,l in [(1,(0,-40,.04)),(72,(.018,-39.75,.025)),(END,(-.014,-40,.045))]: kloc(cam,f,l)
smooth(cam)
if cam.animation_data and cam.animation_data.action:
    for fc in cam.animation_data.action.fcurves:
        if fc.data_path=='location':
            n=fc.modifiers.new(type='NOISE'); n.strength=.0025; n.scale=32

sm=pmat('SunMat',(1,.68,.12),(.98,.62,.12),5.4,.3); sun=sphere('Sun',(0,0,0),2.0,sm,160,96)
nt=sm.node_tree; bs=nt.nodes['Principled BSDF']; noise=nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=8; noise.inputs['Detail'].default_value=5; noise.inputs['Roughness'].default_value=.65
ramp=nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color=(.88,.16,.015,1); ramp.color_ramp.elements[1].color=(1,.88,.20,1)
nt.links.new(noise.outputs['Fac'],ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'],bs.inputs['Base Color'])
if 'Emission Color' in bs.inputs: nt.links.new(ramp.outputs['Color'],bs.inputs['Emission Color'])

corona_plane('CoronaInner',7.2,-.08,.265,.286,.34,.49,3.4,5.0,(1.08,.92,1))
corona_plane('CoronaOuter',9.8,-.02,.19,.205,.30,.49,1.6,3.2,(1.22,.84,1))

mm=pmat('MoonMat',(.004,.005,.007),None,0,.98); moon=sphere('Moon',(-3.1,-18,.14),1.125,mm,144,80)
mn=mm.node_tree.nodes.new('ShaderNodeTexNoise'); mn.inputs['Scale'].default_value=18; mn.inputs['Detail'].default_value=4
bump=mm.node_tree.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.2; bump.inputs['Distance'].default_value=.07
mm.node_tree.links.new(mn.outputs['Fac'],bump.inputs['Height']); mm.node_tree.links.new(bump.outputs['Normal'],mm.node_tree.nodes['Principled BSDF'].inputs['Normal'])
for f,loc in [(1,(-3.1,-18,.15)),(34,(-2.05,-18,.11)),(50,(-1.15,-18,.075)),(62,(-.55,-18,.04)),(68,(-.18,-18,.015)),(72,(0,-18,0)),(76,(.18,-18,-.015)),(82,(.55,-18,-.04)),(94,(1.15,-18,-.075)),(110,(2.05,-18,-.11)),(END,(3.1,-18,-.15))]: kloc(moon,f,loc)
smooth(moon)

bm=pmat('DiamondMat',(1,1,.92),(1,1,.92),28,.1)
right=sphere('DiamondRight',(2.02,-.18,0),.055,bm,32,16); left=sphere('DiamondLeft',(-2.02,-.18,0),.055,bm,32,16)
for o,a,b in [(right,64,68),(left,77,81)]:
    khide(o,1,True); khide(o,a-1,True); khide(o,a,False); khide(o,b,False); khide(o,b+1,True); khide(o,END,True); smooth(o)

random.seed(23); stm=pmat('Stars',(1,1,1),(1,1,1),3.2,.1)
for i in range(28):
    s=sphere(f'Star{i}',(random.uniform(-4.5,4.5),3.0,random.uniform(-2.5,2.5)),random.uniform(.008,.022),stm,12,6)
    khide(s,1,True); khide(s,62,True); khide(s,63,False); khide(s,87,False); khide(s,88,True); khide(s,END,True); smooth(s)

scene.use_nodes=True; cn=scene.node_tree; cn.nodes.clear(); rl=cn.nodes.new('CompositorNodeRLayers'); gl=cn.nodes.new('CompositorNodeGlare'); gl.glare_type='FOG_GLOW'; gl.quality='HIGH'; gl.threshold=.85; gl.size=7; comp=cn.nodes.new('CompositorNodeComposite'); cn.links.new(rl.outputs['Image'],gl.inputs['Image']); cn.links.new(gl.outputs['Image'],comp.inputs['Image'])

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'solar_eclipse_v2.blend'))
print('RENDERING REALISTIC V2')
bpy.ops.render.render(animation=True)
print('DONE')
