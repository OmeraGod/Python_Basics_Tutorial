import bpy, math, os
OUT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','out_fast')); os.makedirs(OUT,exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
s=bpy.context.scene; s.render.engine='BLENDER_EEVEE'; s.render.resolution_x=960; s.render.resolution_y=540; s.render.resolution_percentage=100; s.render.fps=24; s.frame_start=1; s.frame_end=96
s.render.image_settings.file_format='FFMPEG'; s.render.ffmpeg.format='MPEG4'; s.render.ffmpeg.codec='H264'; s.render.ffmpeg.constant_rate_factor='MEDIUM'; s.render.ffmpeg.audio_codec='NONE'; s.render.filepath=os.path.join(OUT,'solar_eclipse_blender.mp4')
w=bpy.data.worlds[0]; w.use_nodes=True; w.node_tree.nodes['Background'].inputs['Color'].default_value=(0.001,0.001,0.005,1); w.node_tree.nodes['Background'].inputs['Strength'].default_value=.02

def mat(n,c,e=None,es=0,r=.5):
 m=bpy.data.materials.new(n); m.use_nodes=True; b=m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value=(*c,1); b.inputs['Roughness'].default_value=r
 if e: b.inputs['Emission Color'].default_value=(*e,1); b.inputs['Emission Strength'].default_value=es
 return m

def sph(n,p,r,m):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=32, radius=r, location=p); o=bpy.context.object; o.name=n; o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o
sun=sph('Sun',(0,0,0),3.8,mat('SunMat',(1,.12,.005),(1,.2,.005),7,.25))
bpy.ops.object.light_add(type='POINT',location=(0,0,0)); bpy.context.object.data.energy=7000; bpy.context.object.data.color=(1,.55,.25); bpy.context.object.data.shadow_soft_size=3.8
earth=sph('Earth',(22,0,0),2.0,mat('EarthMat',(.015,.12,.38),None,0,.7))
# simple land patches
for p,sc in [((21.3,-.3,.8),(1.1,.25,.55)),((21.35,.25,-.7),(.8,.2,.45)),((21.4,.55,.15),(.6,.16,.3))]:
 bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=.65, location=p); o=bpy.context.object; o.scale=sc; o.data.materials.append(mat('Land',(.08,.3,.05),None,0,.8))
moon=sph('Moon',(13,-4,0),.72,mat('MoonMat',(.08,.085,.095),None,0,.95))
for f,y in [(1,-4),(36,-1.2),(48,0),(60,1.2),(96,4)]: moon.location=(13,y,0); moon.keyframe_insert('location',frame=f)
# visible umbra cone
bpy.ops.mesh.primitive_cone_add(vertices=48,radius1=.48,radius2=.08,depth=8.2,location=(17.2,0,0),rotation=(0,math.radians(90),0)); cone=bpy.context.object; cone.data.materials.append(mat('Umbra',(.005,.005,.008),None,0,1))
for f,sc in [(1,(1,.001,.001)),(32,(1,.001,.001)),(42,(1,1,1)),(58,(1,1,1)),(68,(1,.001,.001))]: cone.scale=sc; cone.keyframe_insert('scale',frame=f)
# camera
bpy.ops.object.empty_add(type='PLAIN_AXES',location=(11,0,0)); tgt=bpy.context.object
bpy.ops.object.camera_add(location=(11,-27,8)); cam=bpy.context.object; s.camera=cam; cam.data.lens=47
c=cam.constraints.new(type='TRACK_TO'); c.target=tgt; c.track_axis='TRACK_NEGATIVE_Z'; c.up_axis='UP_Y'
for f,cp,tp in [(1,(11,-27,8),(11,0,0)),(48,(12,-22,5),(12,0,0)),(72,(16,-20,4),(17,0,0)),(96,(11,-27,8),(11,0,0))]: cam.location=cp; cam.keyframe_insert('location',frame=f); tgt.location=tp; tgt.keyframe_insert('location',frame=f)
# title text facing camera-ish
bpy.ops.object.text_add(location=(11,-5.2,6.8),rotation=(math.radians(72),0,0)); t=bpy.context.object; t.data.body='HIỆN TƯỢNG NHẬT THỰ'; t.data.align_x='CENTER'; t.data.size=.65; t.data.extrude=.015; t.data.materials.append(mat('Text',(1,.9,.7),(1,.3,.05),1.5,.4))
# compositor glow
s.use_nodes=True; n=s.node_tree.nodes; l=s.node_tree.links; n.clear(); rl=n.new('CompositorNodeRLayers'); g=n.new('CompositorNodeGlare'); g.glare_type='FOG_GLOW'; g.quality='MEDIUM'; g.threshold=1; g.size=6; co=n.new('CompositorNodeComposite'); l.new(rl.outputs['Image'],g.inputs['Image']); l.new(g.outputs['Image'],co.inputs['Image'])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,'solar_eclipse_blender.blend'))
bpy.ops.render.render(animation=True)
print('FAST_RENDER_DONE')