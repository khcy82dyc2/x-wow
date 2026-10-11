"""The Realistic view's Blender scene: build an exported concept model in a plain studio and render its views.

Run inside Blender by tools/render/realistic_view.py (never by hand needed):
    blender -b --factory-startup -noaudio --python-exit-code 1 --python scene.py -- --input export.json --out DIR
        [--samples 256] [--views front,top] [--width 1600] [--height 1000]   (default: every view in the export)

What it does, and what it refuses to do (the rule: a render shows only what the design has):
- every mesh comes from the export, unchanged in shape: the only geometry work is merging the seams three.js leaves,
  a small edge bevel and a 1 mm wall on open tubes, as a real part has; it checks each part's size against the export;
- materials come from each mesh's own `mat` hint in the model file (the library below), nothing else;
- the setting is a plain dark floor and soft studio lights: no bench, no props, nothing touching the instrument, and
  every light on the instrument itself is off (its LEDs are clear plastic here, not glowing);
- for each view it casts rays at points on every part and records which parts the camera can see, so the page can
  say how many of the model's parts each image shows.
Writes DIR/<view>.png and DIR/render-info.json.
"""
import json
import math
import os
import random
import sys
import time

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = {"samples": "256", "views": "", "width": "1600", "height": "1000"}
for i in range(0, len(argv) - 1, 2):
    opt[argv[i].lstrip("-")] = argv[i + 1]
data = json.load(open(opt["input"], encoding="utf-8"))
OUT = os.path.abspath(opt["out"])   # Blender reads a relative path from the drive root: it once wrote outside the work folder
if not os.path.isdir(OUT):
    raise SystemExit(f"scene.py: the output folder {OUT} must exist (realistic_view.py makes it)")
SAMPLES = int(opt["samples"])

# the views, from the model's own file (or realistic_view.py's plain defaults): azimuth from the model's front (+z in
# three.js) towards its right (+x), elevation above the floor, in degrees
VIEWS = {v["id"]: (float(v["az"]), float(v["el"])) for v in data.get("views") or []}
if not VIEWS:
    raise SystemExit("scene.py: the export lists no views (realistic_view.py writes them)")
LENS = 70        # mm on a 36 mm sensor: a product-photo perspective, with little distortion
CM = 0.01        # the model is in centimetres; Blender works in metres

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"


def to_blender(x, y, z):
    """three.js (x right, y up, z towards the viewer), cm  ->  Blender (x right, y away, z up), m"""
    return (x * CM, -z * CM, y * CM)


# ---------------------------------------------------------------- materials (what each `mat` hint means)
def principled(name, base=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, **kw):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    names = {"transmission": "Transmission Weight", "ior": "IOR", "coat": "Coat Weight", "coat_rough": "Coat Roughness",
             "aniso": "Anisotropic", "sss": "Subsurface Weight", "sss_scale": "Subsurface Scale",
             "film": "Thin Film Thickness", "film_ior": "Thin Film IOR", "spec": "Specular IOR Level"}
    for k, v in kw.items():
        if k == "bump":
            continue
        sock = b.inputs.get(names[k])
        if sock is not None:   # Thin film arrived in Blender 4.2; older versions skip it
            sock.default_value = v
    if kw.get("bump"):   # a faint surface texture, so printed plastic doesn't look like a perfect CG solid
        nt = m.node_tree
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = kw["bump"]
        coord = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.04
        nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


LIB = {
    "pla": dict(base=(0.74, 0.745, 0.735), rough=0.5, spec=0.45, bump=900),
    "pla-black": dict(base=(0.022, 0.022, 0.024), rough=0.52, spec=0.45, bump=900),
    "steel": dict(base=(0.62, 0.62, 0.63), rough=0.3, metal=1.0, aniso=0.35),
    "chrome": dict(base=(0.9, 0.9, 0.9), rough=0.1, metal=1.0),
    "aluminium": dict(base=(0.9, 0.91, 0.91), rough=0.36, metal=1.0),
    "brass": dict(base=(0.9, 0.73, 0.42), rough=0.28, metal=1.0),
    "black-metal": dict(base=(0.02, 0.02, 0.022), rough=0.34, metal=0.3),
    "glass": dict(base=(1.0, 1.0, 1.0), rough=0.0, transmission=1.0, ior=1.52),
    "acrylic": dict(base=(1.0, 1.0, 1.0), rough=0.02, transmission=1.0, ior=1.49),
    "hydrogel": dict(base=(0.93, 0.97, 1.0), rough=0.04, transmission=1.0, ior=1.34),
    "silicone": dict(base=(0.95, 0.95, 0.93), rough=0.35, transmission=0.85, ior=1.41),
    "polariser": dict(base=(0.3, 0.3, 0.31), rough=0.05, transmission=1.0, ior=1.5),
    "diffuser": dict(base=(0.97, 0.97, 0.97), rough=0.7, transmission=1.0, ior=1.49),
    "filter-blue": dict(base=(0.3, 0.55, 1.0), rough=0.02, transmission=1.0, ior=1.52, film=350.0, film_ior=1.9),
    "filter-green": dict(base=(0.4, 1.0, 0.5), rough=0.02, transmission=1.0, ior=1.52, film=420.0, film_ior=1.9),
    "dichroic": dict(base=(0.92, 0.96, 1.0), rough=0.02, transmission=1.0, ior=1.52, film=480.0, film_ior=2.1),
    "pcb-green": dict(base=(0.02, 0.2, 0.075), rough=0.32, coat=0.6, coat_rough=0.12),
    "pcb-black": dict(base=(0.015, 0.015, 0.017), rough=0.32, coat=0.5, coat_rough=0.12),
    "alu-board": dict(base=(0.86, 0.86, 0.84), rough=0.35, coat=0.4, coat_rough=0.1),
    "chip": dict(base=(0.03, 0.03, 0.034), rough=0.55),
    "sensor": dict(base=(0.04, 0.04, 0.06), rough=0.12, metal=0.2, coat=1.0, coat_rough=0.02, film=300.0, film_ior=1.8),
    "plastic-black": dict(base=(0.02, 0.02, 0.022), rough=0.42),
    "plastic-white": dict(base=(0.85, 0.85, 0.82), rough=0.45),
    "plastic-blue": dict(base=(0.05, 0.17, 0.52), rough=0.38),
    "ribbon": dict(base=(0.82, 0.8, 0.74), rough=0.5),
    "wire": dict(base=(0.11, 0.11, 0.12), rough=0.45),
    "hdpe": dict(base=(0.88, 0.88, 0.85), rough=0.5, sss=0.5, sss_scale=0.004),
    "led": dict(base=(1.0, 1.0, 1.0), rough=0.1, transmission=1.0, ior=1.5),
}
SEE_THROUGH = {"glass", "acrylic", "hydrogel", "silicone", "polariser", "diffuser", "filter-blue", "filter-green",
               "dichroic", "led"}
MATS = {}


def material(name):
    if name not in LIB:
        raise SystemExit(f"scene.py: no material '{name}' in the library (model file asks for it)")
    if name not in MATS:
        MATS[name] = principled(name, **LIB[name])
    return MATS[name]


# ---------------------------------------------------------------- the model, part by part
SHARP = math.radians(35)
parts_out = []
OBJ_PART = {}
for part in data["parts"]:
    coll = bpy.data.collections.new("part." + part["id"])
    scene.collection.children.link(coll)
    objs = []
    for j, m in enumerate(part["meshes"]):
        v, idx = m["v"], m["i"]
        verts = [to_blender(v[i], v[i + 1], v[i + 2]) for i in range(0, len(v), 3)]
        faces = [tuple(idx[i:i + 3]) for i in range(0, len(idx), 3)]
        me = bpy.data.meshes.new(f"{part['id']}.{j:02d}")
        me.from_pydata(verts, [], faces)
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-6)   # three.js splits seams; a real part has none
        smooth_all = m["shape"] in ("torus", "wire")
        for f in bm.faces:
            f.smooth = True
        for e in bm.edges:
            if not smooth_all and len(e.link_faces) == 2 and e.calc_face_angle(0.0) > SHARP:
                e.smooth = False
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(me.name, me)
        coll.objects.link(ob)
        me.materials.append(material(m["mat"]))
        ob["x_mat"] = m["mat"]
        ob.pass_index = part["index"] + 1
        dims = sorted(ob.dimensions) if any(ob.dimensions) else [0, 0, 0]
        if m["shape"] == "tube-open":
            sol = ob.modifiers.new("wall", "SOLIDIFY")
            sol.thickness = 0.001
            sol.offset = -1.0          # inward, so the outside stays where the model put it
        if m["shape"] in ("box", "cyl", "tube-open"):
            bev = ob.modifiers.new("edge", "BEVEL")
            bev.limit_method = "ANGLE"
            bev.angle_limit = SHARP
            bev.width = max(0.00004, min(0.0003, 0.2 * (dims[0] or dims[1] or 0.001)))
            bev.segments = 3
            bev.use_clamp_overlap = True
            bev.harden_normals = True
        objs.append(ob)
        OBJ_PART[ob.name] = part["id"]
    parts_out.append({"id": part["id"], "index": part["index"], "objects": [o.name for o in objs], "meshes": len(objs)})

# scale check: each part's box in Blender, turned back into the export's frame, must equal the export's own box
depsgraph = bpy.context.evaluated_depsgraph_get()
worst_raw, worst_eval = 0.0, 0.0
for part, info in zip(data["parts"], parts_out):
    raw, ev = [], []
    for name in info["objects"]:
        ob = bpy.data.objects[name]
        raw += [ob.matrix_world @ vv.co for vv in ob.data.vertices]
        oe = ob.evaluated_get(depsgraph)
        ev += [oe.matrix_world @ vv.co for vv in oe.to_mesh().vertices]
        oe.to_mesh_clear()
    def box(pts):
        # back to three.js cm: x = X/CM, y = Z/CM, z = -Y/CM
        xs = [p.x / CM for p in pts]; ys = [p.z / CM for p in pts]; zs = [-p.y / CM for p in pts]
        return [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]
    want = part["bbox"]
    d_raw = max(abs(a - b) for a, b in zip(box(raw), want))
    d_eval = max(abs(a - b) for a, b in zip(box(ev), want))
    info.update(bbox_cm=[round(x, 4) for x in want], dev_raw_cm=round(d_raw, 6), dev_eval_cm=round(d_eval, 4))
    worst_raw, worst_eval = max(worst_raw, d_raw), max(worst_eval, d_eval)
scale_ok = worst_raw < 1e-3 and worst_eval < 0.03   # import exact to 10 µm; bevels and walls stay inside 0.3 mm

# ---------------------------------------------------------------- the studio: a plain floor, soft light, nothing else
xs = [p for part in data["parts"] for p in (part["bbox"][0], part["bbox"][3])]
ys = [p for part in data["parts"] for p in (part["bbox"][1], part["bbox"][4])]
zs = [p for part in data["parts"] for p in (part["bbox"][2], part["bbox"][5])]
lo, hi = Vector(to_blender(min(xs), min(ys), max(zs))), Vector(to_blender(max(xs), max(ys), min(zs)))
lo, hi = Vector((min(lo.x, hi.x), min(lo.y, hi.y), min(lo.z, hi.z))), Vector((max(lo.x, hi.x), max(lo.y, hi.y), max(lo.z, hi.z)))
centre = (lo + hi) / 2
size = (hi - lo).length

bpy.ops.mesh.primitive_circle_add(vertices=96, radius=8.0, fill_type="NGON", location=(centre.x, centre.y, 0.0))
floor = bpy.context.active_object
floor.name = "studio.floor"
floor.data.materials.append(principled("studio-floor", base=(0.032, 0.036, 0.043), rough=0.62, spec=0.3))

world = bpy.data.worlds.new("studio")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.008, 0.009, 0.012, 1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0


def area(name, at, power, size_m, colour=(1.0, 1.0, 1.0)):
    light = bpy.data.lights.new(name, "AREA")
    light.energy = power
    light.size = size_m
    light.color = colour
    ob = bpy.data.objects.new(name, light)
    scene.collection.objects.link(ob)
    ob.location = centre + Vector(at)
    ob.rotation_euler = (centre - ob.location).to_track_quat("-Z", "Y").to_euler()
    return ob


area("studio.key", (-0.95, -1.15, 1.25), 34, 1.1, (1.0, 0.97, 0.93))
area("studio.fill", (1.35, -0.7, 0.55), 10, 1.4, (0.9, 0.95, 1.0))
area("studio.rim", (0.5, 1.3, 0.85), 26, 0.8, (0.92, 0.96, 1.0))
area("studio.rim2", (-1.2, 0.9, 0.7), 14, 0.8, (1.0, 0.97, 0.94))
area("studio.top", (0.0, 0.0, 1.7), 14, 1.6)

# ---------------------------------------------------------------- render settings
scene.render.engine = "CYCLES"
device = "CPU"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        try:
            prefs.compute_device_type = kind
        except TypeError:
            continue
        prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type == kind]
        if gpus:
            for d in prefs.devices:
                d.use = d.type == kind
            device = kind
            break
except Exception as e:  # noqa: BLE001
    print("scene.py: no GPU device, rendering on the CPU:", e)
scene.cycles.device = "GPU" if device != "CPU" else "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.01
scene.cycles.use_denoising = True
scene.cycles.denoiser = "OPENIMAGEDENOISE"
scene.cycles.seed = 0
scene.cycles.max_bounces = 16
scene.cycles.transmission_bounces = 16
scene.cycles.transparent_max_bounces = 16
scene.cycles.glossy_bounces = 8
scene.cycles.caustics_reflective = False
scene.cycles.caustics_refractive = False
scene.cycles.blur_glossy = 1.0
scene.render.resolution_x = int(opt["width"])
scene.render.resolution_y = int(opt["height"])
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.color_depth = "8"
scene.view_settings.view_transform = "AgX"
for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
    try:
        scene.view_settings.look = look
        break
    except TypeError:
        continue
scene.view_settings.exposure = 0.0

# ---------------------------------------------------------------- cameras fitted to the whole model
cam_data = bpy.data.cameras.new("studio.camera")
cam_data.lens = LENS
cam_data.sensor_width = 36
cam_data.sensor_fit = "HORIZONTAL"
cam = bpy.data.objects.new("studio.camera", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

all_pts = []
for info in parts_out:
    for name in info["objects"]:
        ob = bpy.data.objects[name]
        all_pts += [ob.matrix_world @ vv.co for vv in list(ob.data.vertices)[::3]]


def aim(az, el, dist):
    a, e = math.radians(az), math.radians(el)
    d3 = (math.sin(a) * math.cos(e), math.sin(e), math.cos(a) * math.cos(e))     # three.js direction
    d = Vector((d3[0], -d3[2], d3[1]))
    cam.location = centre + d * dist
    cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()


def fits(margin=0.06):
    for p in all_pts:
        c = world_to_camera_view(scene, cam, p)
        if c.z <= 0 or not (margin <= c.x <= 1 - margin and margin <= c.y <= 1 - margin):
            return False
    return True


def fit(az, el):
    """Nearest camera distance that keeps every point of the model inside the frame, then the lens shift that centres
    it (a shift moves the frame, not the viewpoint, so the perspective is unchanged); three rounds settle both."""
    cam_data.shift_x = cam_data.shift_y = 0.0
    aspect = scene.render.resolution_y / scene.render.resolution_x
    for _ in range(3):
        near, far = size * 0.5, size * 20
        for _ in range(40):
            mid = (near + far) / 2
            aim(az, el, mid)
            if fits():
                far = mid
            else:
                near = mid
        aim(az, el, far)
        cs = [world_to_camera_view(scene, cam, p) for p in all_pts]
        x0, x1 = min(c.x for c in cs), max(c.x for c in cs)
        y0, y1 = min(c.y for c in cs), max(c.y for c in cs)
        cam_data.shift_x += ((x0 + x1) / 2 - 0.5)
        cam_data.shift_y += ((y0 + y1) / 2 - 0.5) * aspect
    bpy.context.view_layer.update()
    print(f"scene.py: fit az {az} el {el}: {far:.3f} m, shift {cam_data.shift_x:+.3f} {cam_data.shift_y:+.3f}; "
          f"frame x {x0:.3f}-{x1:.3f}, y {y0:.3f}-{y1:.3f} before the last shift")
    return far


# ---------------------------------------------------------------- which parts each view can see
rng = random.Random(0)


def sample_points(info, n=420):
    tris = []
    for name in info["objects"]:
        ob = bpy.data.objects[name]
        me = ob.data
        me.calc_loop_triangles()
        for t in me.loop_triangles:
            a, b, c = (ob.matrix_world @ me.vertices[i].co for i in t.vertices)
            tris.append((a, b, c, ((b - a).cross(c - a)).length / 2))
    total = sum(t[3] for t in tris) or 1.0
    pts = []
    for a, b, c, w in tris:
        k = w / total * n
        cnt = int(k) + (1 if rng.random() < k - int(k) else 0)
        for _ in range(cnt):
            r1, r2 = rng.random(), rng.random()
            if r1 + r2 > 1:
                r1, r2 = 1 - r1, 1 - r2
            pts.append(a + (b - a) * r1 + (c - a) * r2)
    return pts


SAMPLES_BY_PART = {info["id"]: sample_points(info) for info in parts_out}


def visible_parts():
    dg = bpy.context.evaluated_depsgraph_get()
    counts = {}
    origin = cam.location.copy()
    for pid, pts in SAMPLES_BY_PART.items():
        seen = 0
        for p in pts:
            c = world_to_camera_view(scene, cam, p)
            if c.z <= 0 or not (0 <= c.x <= 1 and 0 <= c.y <= 1):
                continue
            o = origin.copy()
            d = (p - o)
            dist = d.length
            d.normalize()
            for _ in range(12):   # look through glass, film and clear plastic of other parts
                hit, loc, _n, _i, obj, _m = scene.ray_cast(dg, o, d, distance=dist - (o - origin).length + 1e-4)
                if not hit:
                    seen += 1      # nothing in the way (the point itself sits on a face the ray grazed)
                    break
                owner = OBJ_PART.get(obj.name)
                if owner == pid:
                    seen += 1
                    break
                if owner and obj.get("x_mat") in SEE_THROUGH:
                    o = loc + d * 1e-5
                    continue
                break
        counts[pid] = seen
    return counts


# ---------------------------------------------------------------- render
info = {"blender": bpy.app.version_string, "device": device, "samples": SAMPLES, "seed": 0, "lens_mm": LENS,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y], "parts": parts_out,
        "scale_ok": scale_ok, "worst_raw_cm": round(worst_raw, 6), "worst_eval_cm": round(worst_eval, 4),
        "materials": sorted(MATS), "views": []}
for vid in [v for v in opt["views"].split(",") if v] or list(VIEWS):
    az, el = VIEWS[vid]
    dist = fit(az, el)
    counts = visible_parts()
    t0 = time.time()
    scene.render.filepath = f"{OUT}/{vid}.png"
    bpy.ops.render.render(write_still=True)
    info["views"].append({"id": vid, "az": az, "el": el, "distance_m": round(dist, 4), "render_s": round(time.time() - t0, 1),
                          "points": {k: len(v) for k, v in SAMPLES_BY_PART.items()}, "seen": counts,
                          "visible": [k for k, n in counts.items() if n >= 3]})
    print(f"scene.py: {vid} rendered in {info['views'][-1]['render_s']} s; shows {len(info['views'][-1]['visible'])} of {len(parts_out)} parts")
json.dump(info, open(f"{OUT}/render-info.json", "w", encoding="utf-8"), indent=1)
print("scene.py: done", "scale ok" if scale_ok else "SCALE MISMATCH", info["worst_raw_cm"], info["worst_eval_cm"])
