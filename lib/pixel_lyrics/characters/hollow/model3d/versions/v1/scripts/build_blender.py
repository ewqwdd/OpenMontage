"""Stage 2: spec.json -> rigged Blender model, GLB, check renders.

  blender -b -P build_blender.py -- [--views] [--turn N] [--anim]

Reads work/spec.json + work/atlas.png (written by make_spec.py). Writes hollow.blend, hollow.glb and renders to
work/render/. The rest pose is the A-pose of the drawing; "stand" lowers the arms like the character sheet.
Materials are emission-only with closest filtering, view transform Standard: a rendered pixel is a drawing pixel.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SPEC = json.loads((WORK / "spec.json").read_text(encoding="utf-8"))
HEIGHT_M = 1.75
S = HEIGHT_M / SPEC["px_height"]
CX, SOLE = SPEC["cx"], SPEC["sole_y"]


def P(p):
    """drawing pixels (x, y down, d towards the viewer) -> Blender metres (X his left, -Y forward, Z up)."""
    return Vector(((p[0] - CX) * S, -p[2] * S, (SOLE - p[1]) * S))


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection

# ---------------------------------------------------------------- material
SMOOTH = "--smooth" in ARGS                     # the atlas with the dither smoothed -> hollow_smooth.glb
TAG = "_smooth" if SMOOTH else ""
img = bpy.data.images.load(str(WORK / f"atlas{TAG}.png"))
img.pack()
mat = bpy.data.materials.new("hollow_pixels")
mat.use_nodes = True
nt = mat.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
tex = nt.nodes.new("ShaderNodeTexImage")
tex.image, tex.interpolation = img, "Closest"
emi = nt.nodes.new("ShaderNodeEmission")
tra = nt.nodes.new("ShaderNodeBsdfTransparent")
mix = nt.nodes.new("ShaderNodeMixShader")
cut = nt.nodes.new("ShaderNodeMath")
cut.operation = "GREATER_THAN"
cut.inputs[1].default_value = 0.5
outn = nt.nodes.new("ShaderNodeOutputMaterial")
# The exact shape below is what Blender's glTF exporter recognises as KHR_materials_unlit with an alpha cut-off
# (io_scene_gltf2/blender/exp/material/unlit.py): alpha mix with Transparent, then the "light path" mix, then Emission.
lp = nt.nodes.new("ShaderNodeLightPath")
tra2 = nt.nodes.new("ShaderNodeBsdfTransparent")
mix2 = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(tex.outputs["Color"], emi.inputs["Color"])
nt.links.new(lp.outputs["Is Camera Ray"], mix2.inputs[0])
nt.links.new(tra2.outputs[0], mix2.inputs[1])
nt.links.new(emi.outputs[0], mix2.inputs[2])
nt.links.new(tex.outputs["Alpha"], cut.inputs[0])
nt.links.new(cut.outputs[0], mix.inputs[0])
nt.links.new(tra.outputs[0], mix.inputs[1])
nt.links.new(mix2.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], outn.inputs["Surface"])
mat.use_backface_culling = False
for attr, val in (("blend_method", "CLIP"), ("surface_render_method", "DITHERED")):
    try:
        setattr(mat, attr, val)
    except Exception:
        pass

# ---------------------------------------------------------------- armature
arm_data = bpy.data.armatures.new("hollow_rig")
arm = bpy.data.objects.new("hollow_rig", arm_data)
col.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
for b in SPEC["bones"]:
    eb = arm_data.edit_bones.new(b["name"])
    eb.head, eb.tail = P(b["head"]), P(b["tail"])
    if b["parent"]:
        eb.parent = arm_data.edit_bones[b["parent"]]
        eb.use_connect = b["connect"]
bpy.ops.object.mode_set(mode="OBJECT")
arm_data.display_type = "STICK"

# ---------------------------------------------------------------- meshes
OBJ = {}
for o in SPEC["objects"]:
    me = bpy.data.meshes.new(o["name"])
    me.from_pydata([P(v) for v in o["verts"]], [], o["faces"])
    uvl = me.uv_layers.new(name="UVMap")
    for poly, fuv in zip(me.polygons, o["uvs"]):
        for li, uv in zip(poly.loop_indices, fuv):
            uvl.data[li].uv = uv
    me.materials.append(mat)
    ob = bpy.data.objects.new(o["name"], me)
    col.objects.link(ob)
    for vi, ws in enumerate(o["weights"]):
        for name, w in ws:
            vg = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
            vg.add([vi], w, "REPLACE")
    ob.parent = arm
    md = ob.modifiers.new("Armature", "ARMATURE")
    md.object = arm
    ob["part"] = o["name"]
    OBJ[o["name"]] = ob
    for p in me.polygons:
        p.use_smooth = True
bpy.context.view_layer.update()
print("built", {k: len(v.data.vertices) for k, v in OBJ.items()})


# ---------------------------------------------------------------- posing
def turn(bone, deg, axis="Y"):
    """Rotate a pose bone around a WORLD axis through its head.
    Y: clockwise on screen in the front view. X: negative swings a hanging limb forward. ROLL: round its own length."""
    pb = arm.pose.bones[bone]
    if axis == "ROLL":
        pb.matrix = pb.matrix @ Matrix.Rotation(math.radians(deg), 4, "Y")
        bpy.context.view_layer.update()
        return
    Mw = arm.matrix_world @ pb.matrix
    piv = Mw.translation.copy()
    R = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-piv)
    pb.matrix = arm.matrix_world.inverted() @ R @ Mw
    bpy.context.view_layer.update()


STAND = [("upper_arm.R", -48, "Y"), ("upper_arm.L", 48, "Y"), ("forearm.R", -4, "Y"), ("forearm.L", 4, "Y"),
         ("forearm.R", 70, "ROLL"), ("forearm.L", -70, "ROLL"),          # palms towards the thighs
         ("thigh.R", -3, "Y"), ("thigh.L", 3, "Y")]


def walk(ph):
    """Walk on the spot, ph = 0..1 over one cycle (two steps)."""
    a = 2 * math.pi * ph
    sw = math.sin(a)
    out = list(STAND)
    for sd, k in (("R", 1), ("L", -1)):
        out += [(f"thigh.{sd}", -24 * sw * k, "X"),
                (f"shin.{sd}", 38 * max(0.0, math.sin(a * 1 + (0.6 if k > 0 else math.pi + 0.6))), "X"),
                (f"upper_arm.{sd}", 18 * sw * k, "X"),
                (f"forearm.{sd}", -10 - 8 * max(0.0, -sw * k), "X")]
    out += [("spine", 2.5 * math.sin(a), "Z"), ("head", -2.0 * math.sin(a), "Z")]
    return out


POSES = {"apose": [], "stand": STAND}


def set_pose(pose):
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    for bone, deg, axis in (POSES[pose] if isinstance(pose, str) else pose):
        turn(bone, deg, axis)


def bake_action(name, poses):
    """poses: list of pose lists, one per frame (1-based). Leaves the action stashed on its own NLA track."""
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    arm.animation_data_create()
    act = bpy.data.actions.new(name)
    arm.animation_data.action = act
    for f, pose in enumerate(poses, start=1):
        set_pose(pose)
        for pb in arm.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=f)
    act.use_fake_user = True
    tr = arm.animation_data.nla_tracks.new()
    tr.name = name
    tr.strips.new(name, 1, act)
    tr.mute = True
    arm.animation_data.action = None
    return act


# ---------------------------------------------------------------- render setup
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        scene.render.engine = eng
        break
    except Exception:
        continue
scene.view_settings.view_transform = "Standard"
scene.render.film_transparent = True
scene.render.filter_size = 0.6
try:
    scene.eevee.taa_render_samples = 16
except Exception:
    pass
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam = bpy.data.objects.new("cam", cam_data)
col.objects.link(cam)
scene.camera = cam
RDIR = WORK / f"render{TAG}"
RDIR.mkdir(exist_ok=True)


def shoot(name, az, px=1024, elev=0.0):
    """Orthographic shot where image row y is drawing row y and, head-on, image pixels are drawing pixels."""
    scene.render.resolution_x = scene.render.resolution_y = px
    scene.render.resolution_percentage = 100
    cam_data.ortho_scale = 1024 * S
    a, e = math.radians(az), math.radians(elev)
    d = Vector((-math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    right = Vector((math.cos(a), -math.sin(a), 0))
    target = Vector((0, 0, (SOLE - 512) * S)) + right * ((512 - CX) * S)
    cam.location = target + d * 6
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(RDIR / name)
    bpy.ops.render.render(write_still=True)


AZ = {"front": 0, "front34": -45, "side": 90, "back34": 135, "back": 180}
if "--debug-head" in ARGS:
    set_pose("stand")
    for tag, hidden in (("skull", ["head_shell"]), ("shell", ["head_skull"])):
        for n_ in OBJ:
            OBJ[n_].hide_render = n_ in hidden or not n_.startswith(("head", "neck"))
        for n_, az in (("f0", 0), ("f34", -45), ("side", 90)):
            shoot(f"dbg_{tag}_{n_}.png", az)
    for n_ in OBJ:
        OBJ[n_].hide_render = False
if "--views" in ARGS:
    set_pose("apose")
    shoot("apose_front.png", 0)
    set_pose("stand")
    for n, az in AZ.items():
        shoot(f"stand_{n}.png", az)
    shoot("stand_high.png", -20, elev=35)
    shoot("stand_low.png", 20, elev=-25)
if "--turn" in ARGS:
    n = int(ARGS[ARGS.index("--turn") + 1])
    set_pose("stand")
    for i in range(n):
        shoot(f"turn_{i:03d}.png", -360.0 * i / n, px=768)
if "--walk" in ARGS:
    n = int(ARGS[ARGS.index("--walk") + 1])
    for i in range(n):
        set_pose(walk(i / n))
        shoot(f"walk34_{i:03d}.png", -35, px=768)
        shoot(f"walkside_{i:03d}.png", 90, px=768)

# ---------------------------------------------------------------- actions, save, export
N_WALK = 24
bake_action("stand", [STAND, STAND])
bake_action("walk_in_place", [walk(i / N_WALK) for i in range(N_WALK + 1)])
set_pose("apose")
scene.frame_start, scene.frame_end = 1, N_WALK + 1
scene.render.fps = 24
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / f"hollow{TAG}.blend"))
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=str(HERE / f"hollow{TAG}.glb"), export_format="GLB", export_yup=True,
                          export_apply=False, export_skins=True, export_animations=True,
                          export_animation_mode="NLA_TRACKS", export_cameras=False, use_selection=False)
print("saved", HERE / f"hollow{TAG}.blend", HERE / f"hollow{TAG}.glb")
