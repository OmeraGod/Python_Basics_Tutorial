import bpy, math, os, random
from mathutils import Vector

FPS=24
END=144
OUT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','out4kv3'))
FRAMES=os.path.join(OUT,'frames')
os.makedirs(FRAMES,exist_ok=True)

def clear():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

def look_at(obj,target=(0,0,0)):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def pmat(name,base,em=None,st=0,rough=.5):
    m=bpy.data.materials.new(name); m.use_nodes=True
    b=m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value=(*base,1); b.inputs['Roughness'].default_value=rough
    if em is not None:
        if 'Emission Color' in b.inputs:
            b.inputs['Emission Color'].default_value=(*em,1); b.inputs['Emission Strength'].default_value=st
        else:
            b.inputs['Emission'].default_value=(*em,1); b.inputs['Emission Strength'].default_value=st
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

def corona_mat(name,peak_strength):
    m=bpy.data.materials.new(name); m.use_nodes=True
    nt=m.node_tree; nt.nodes.clear()
    out=nt.nodes.new('ShaderNodeOutputMaterial'); em=nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value=(1.0,.96,.88,1)
    nt.links.new(em.outputs['Emission'],out.inputs['Surface'])
    for f,v in [(1,.02),(48,.025),(60,.08),(64,peak_strength*.25),(68,peak_strength*.65),(72,peak_strength),(78,peak_strength*.8),(84,peak_strength*.3),(90,.08),(104,.025),(END,.02)]:
        em.inputs['Strength'].default_value=v; em.inputs['Strength'].keyframe_insert('default_value',frame=f)
    return m

def curve_ray(name,theta,r0,r1,mat,width,bend=0.0,y=-.10):
    cu=bpy.data.curves.new(name,'CURVE'); cu.dimensions='3D'; cu.resolution_u=1; cu.bevel_depth=width; cu.bevel_resolution=2; cu.resolution_u=2
    sp=cu.splines.new('POLY'); sp.points.add(3)
    for i,t in enumerate((0.0,.32,.68,1.0)):
        r=r0+(r1-r0)*t
        ang=theta + bend*math.sin(math.pi*t)
        x=r*math.cos(ang); z=r*math.sin(ang)
        sp.points[i].co=(x,y,z,1)
    obj=bpy.data.objects.new(name,cu); bpy.context.collection.objects.link(obj); obj.data.materials.append(mat); return obj

clear(); scene=bpy.context.scene
scene.frame_start=1; scene.frame_end=END; scene.render.engine='BLENDER_EEVEE'; scene.render.resolution_x=3840; scene.render.resolution_y=2160; scene.render.resolution_percentage=100; scene.render.fps=FPS
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'; scene.render.filepath=os.path.join(FRAMES,'frame_'); scene.render.film_transparent=False
try: scene.eevee.taa_render_samples=48
except: pass
try: scene.view_settings.look='AgX - Medium High Contrast'
except: pass
scene.view_settings.exposure=-.65

world=bpy.data.worlds[0] if bpy.data.worlds else bpy.data.worlds.new('Sky'); scene.world=world; world.use_nodes=True
bg=world.node_tree.nodes['Background']; bg.inputs['Color'].default_value=(.006,.025,.085,1)
for f,s in [(1,.20),(42,.17),(56,.10),(64,.045),(68,.016),(72,.006),(80,.012),(88,.045),(104,.15),(END,.20)]:
    bg.inputs['Strength'].default_value=s; bg.inputs['Strength'].keyframe_insert('default_value',frame=f)

# telephoto camera
bpy.ops.object.camera_add(location=(0,-40,.035)); cam=bpy.context.object; scene.camera=cam; cam.data.lens=145; cam.data.sensor_width=36; look_at(cam)
for f,l in [(1,(0,-40,.035)),(72,(.012,-39.8,.020)),(END,(-.010,-40,.04))]: kloc(cam,f,l)
smooth(cam)
if cam.animation_data and cam.animation_data.action:
    for fc in cam.animation_data.action.fcurves:
        if fc.data_path=='location':
            n=fc.modifiers.new(type='NOISE'); n.strength=.0018; n.scale=34

# sun
sm=pmat('SunMat',(1,.60,.08),(1,.55,.06),3.2,.28); sun=sphere('Sun',(0,0,0),2.0,sm,160,96)
nt=sm.node_tree; bs=nt.nodes['Principled BSDF']; noise=nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value=9; noise.inputs['Detail'].default_value=5; noise.inputs['Roughness'].default_value=.65
ramp=nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color=(.72,.08,.006,1); ramp.color_ramp.elements[1].color=(1,.75,.12,1)
nt.links.new(noise.outputs['Fac'],ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'],bs.inputs['Base Color'])
if 'Emission Color' in bs.inputs: nt.links.new(ramp.outputs['Color'],bs.inputs['Emission Color'])

# realistic corona built from irregular radial streamers
cmats=[corona_mat('CoronaSoft',1.1),corona_mat('CoronaMid',2.0),corona_mat('CoronaBright',3.6)]
random.seed(2026)
for i in range(260):
    theta=random.random()*math.tau
    # longer equatorial streamers, shorter polar plumes
    equator=abs(math.cos(theta))**2.6
    base_len=random.uniform(.28,.78)
    extra=equator*random.uniform(.55,2.25)
    if random.random()<.07: extra+=random.uniform(.8,1.7)
    r0=random.uniform(2.015,2.070)
    r1=min(4.55,r0+base_len+extra)
    bend=random.uniform(-.035,.035)*(1.0+.7*(1-equator))
    width=random.uniform(.006,.018)*(1.1 if r1<2.8 else .85)
    p=random.random(); mat=cmats[0] if p<.48 else (cmats[1] if p<.86 else cmats[2])
    curve_ray(f'CoronaRay_{i:03d}',theta,r0,r1,mat,width,bend,-.08-random.uniform(0,.04))

# bright inner limb - one very thin ring only
bpy.ops.mesh.primitive_torus_add(major_radius=2.055,minor_radius=.018,major_segments=192,minor_segments=12,location=(0,-.13,0),rotation=(math.radians(90),0,0))
limb=bpy.context.object; limb.data.materials.append(corona_mat('InnerLimb',6.5))

# moon silhouette
mm=pmat('MoonMat',(.0025,.003,.0045),None,0,.98); moon=sphere('Moon',(-3.1,-18,.15),1.125,mm,144,80)
mn=mm.node_tree.nodes.new('ShaderNodeTexNoise'); mn.inputs['Scale'].default_value=19; mn.inputs['Detail'].default_value=4
bump=mm.node_tree.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.16; bump.inputs['Distance'].default_value=.06
mm.node_tree.links.new(mn.outputs['Fac'],bump.inputs['Height']); mm.node_tree.links.new(bump.outputs['Normal'],mm.node_tree.nodes['Principled BSDF'].inputs['Normal'])
for f,loc in [(1,(-3.1,-18,.15)),(34,(-2.05,-18,.11)),(50,(-1.15,-18,.075)),(62,(-.55,-18,.04)),(68,(-.18,-18,.015)),(72,(0,-18,0)),(76,(.18,-18,-.015)),(82,(.55,-18,-.04)),(94,(1.15,-18,-.075)),(110,(2.05,-18,-.11)),(END,(3.1,-18,-.15))]: kloc(moon,f,loc)
smooth(moon)

# diamond-ring flashes
bm=pmat('DiamondMat',(1,1,.90),(1,1,.92),22,.1)
right=sphere('DiamondRight',(2.02,-.20,0),.050,bm,32,16); left=sphere('DiamondLeft',(-2.02,-.20,0),.050,bm,32,16)
for o,a,b in [(right,64,68),(left,77,81)]:
    khide(o,1,True); khide(o,a-1,True); khide(o,a,False); khide(o,b,False); khide(o,b+1,True); khide(o,END,True); smooth(o)

# stars around totality
random.seed(44); stm=pmat('Stars',(1,1,1),(1,1,1),2.4,.1)
for i in range(24):
    s=sphere(f'Star{i:02d}',(random.uniform(-5.0,5.0),3.0,random.uniform(-2.8,2.8)),random.uniform(.007,.018),stm,12,6)
    khide(s,1,True); khide(s,64,True); khide(s,65,False); khide(s,86,False); khide(s,87,True); khide(s,END,True); smooth(s)

# compositor glow softens the procedural corona into camera-like light
scene.use_nodes=True; cn=scene.node_tree; cn.nodes.clear(); rl=cn.nodes.new('CompositorNodeRLayers'); gl=cn.nodes.new('CompositorNodeGlare'); gl.glare_type='FOG_GLOW'; gl.quality='HIGH'; gl.threshold=.45; gl.size=7; comp=cn.nodes.new('CompositorNodeComposite'); cn.links.new(rl.outputs['Image'],gl.inputs['Image']); cn.links.new(gl.outputs['Image'],comp.inputs['Image'])

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'solar_eclipse_v3.blend'))
print('RENDERING V3')
bpy.ops.render.render(animation=True)
print('DONE')
