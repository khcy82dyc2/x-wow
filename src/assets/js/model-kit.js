/* The shape kit every X-WOW concept model is built from: boxes, cylinders, tori and tubes only.
 * The viewer (concept-model.js) and the Realistic view's export both build a model through this file, so the
 * renders in assets/renders/<model>/ are keyed to its SHA-256 as well as the model's (src/data/renders.json):
 * change a shape here and build.py hides every Realistic view until it is re-rendered.
 * Each mesh records its part, its shape and its material hint (mesh.userData) for the export.
 */

export function rimEdges(THREE, rt, rb, h, seg, ribs) {
  const v = [];
  const y0 = -h / 2, y1 = h / 2, TAU = Math.PI * 2;
  for (let i = 0; i < seg; i++) {
    const a0 = (i / seg) * TAU, a1 = ((i + 1) / seg) * TAU;
    if (rt > 0) v.push(rt * Math.sin(a0), y1, rt * Math.cos(a0), rt * Math.sin(a1), y1, rt * Math.cos(a1));
    if (rb > 0) v.push(rb * Math.sin(a0), y0, rb * Math.cos(a0), rb * Math.sin(a1), y0, rb * Math.cos(a1));
  }
  for (let i = 0; i < ribs; i++) {
    const a = (i / ribs) * TAU + Math.PI / 4;
    v.push(rt * Math.sin(a), y1, rt * Math.cos(a), rb * Math.sin(a), y0, rb * Math.cos(a));
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(v, 3));
  return g;
}

/* add(p, parent, geo, edgeGeo, pos, rot, kind) makes and places one mesh and returns it; the kit tags it */
export function makeKit(THREE, add) {
  const tag = (mesh, shape, o) => {
    mesh.userData.shape = shape;
    mesh.userData.mat = o.mat || null;
    return mesh;
  };
  return function kit(p, parent) {
    parent = parent || p.group;
    return {
      box(w, h, d, x, y, z, o = {}) {
        const geo = new THREE.BoxGeometry(w, h, d);
        return tag(add(p, parent, geo, new THREE.EdgesGeometry(geo), [x, y, z], o.rot, o.kind), 'box', o);
      },
      cyl(rt, rb, h, x, y, z, o = {}) {
        const seg = o.seg || 28;
        const geo = new THREE.CylinderGeometry(rt, rb, h, seg, 1, !!o.open);
        return tag(add(p, parent, geo, rimEdges(THREE, rt, rb, h, seg, o.ribs === undefined ? 6 : o.ribs), [x, y, z], o.rot, o.kind),
          o.open ? 'tube-open' : 'cyl', o);
      },
      torus(R, r, x, y, z, o = {}) {
        const geo = new THREE.TorusGeometry(R, r, o.rs || 6, o.ts || 44);
        return tag(add(p, parent, geo, new THREE.EdgesGeometry(geo, 25), [x, y, z], o.rot || [Math.PI / 2, 0, 0], o.kind), 'torus', o);
      },
      tube(pts, r, o = {}) {
        const curve = new THREE.CatmullRomCurve3(pts.map((q) => new THREE.Vector3(q[0], q[1], q[2])));
        const n = o.seg || 48;
        const geo = new THREE.TubeGeometry(curve, n, r, 6, false);
        const line = curve.getPoints(n);
        const v = [];
        for (let i = 0; i < line.length - 1; i++) v.push(line[i].x, line[i].y, line[i].z, line[i + 1].x, line[i + 1].y, line[i + 1].z);
        const eg = new THREE.BufferGeometry();
        eg.setAttribute('position', new THREE.Float32BufferAttribute(v, 3));
        return tag(add(p, parent, geo, eg, [0, 0, 0], null, o.kind || (p.kind === 'r' ? 'rw' : 'cw')), 'wire', o);
      },
    };
  };
}
