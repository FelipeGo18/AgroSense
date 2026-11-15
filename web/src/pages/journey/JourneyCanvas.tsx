import { Canvas, useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState, type MutableRefObject } from "react";
import * as THREE from "three";
import { Mascot3D } from "@/components/mascot/Mascot3D";

/**
 * La escena 3D del recorrido del satélite a la finca (HU-155): low-poly, con sombreado plano, como el resto de la
 * identidad. Se carga aparte (three.js pesa) y solo con movimiento: en modo ligero la página muestra las ilustraciones
 * 2D quietas (HU-158).
 *
 * Cuatro niveles, uno por parada: la Tierra vista desde la órbita, la región (Boyacá y Cundinamarca), el municipio y
 * la finca. `progress` va de 0 a 3 con el scroll; la cámara lo sigue con suavidad. Entre la Tierra y la región se
 * atraviesa una capa de nubes (la niebla sube y baja) que tapa el cambio de lugar. La mascota vuela al lado de la
 * cámara y guía.
 *
 * Es una ilustración: el terreno es inventado (seno de varias frecuencias), no el relieve real (R5). La página lo dice.
 */

const TERRAIN_Y = -100;
const FARM: [number, number] = [6, 2];

/** Relieve de ilustración: cordillera al oeste, valles al este. Plano cerca de la finca. */
function height(x: number, z: number) {
  const ridge = Math.sin(x * 0.18 + 0.7) * 2.2 + Math.cos(z * 0.21) * 1.6 + Math.sin((x + z) * 0.43) * 0.6;
  const west = THREE.MathUtils.smoothstep(-x, -4, 16) * 3.5;
  const flat = THREE.MathUtils.smoothstep(Math.hypot(x - FARM[0], z - FARM[1]), 1.2, 4.5);
  return (ridge + west) * flat;
}

/** Cámara: dónde está y a dónde mira en cada nivel. */
const KEYS: { pos: THREE.Vector3Tuple; look: THREE.Vector3Tuple }[] = [
  { pos: [0, 2, 19], look: [0, 0, 0] },
  { pos: [-2, TERRAIN_Y + 34, 26], look: [0, TERRAIN_Y, 0] },
  { pos: [FARM[0] - 3, TERRAIN_Y + 11, FARM[1] + 10], look: [FARM[0], TERRAIN_Y, FARM[1]] },
  { pos: [FARM[0] - 2.4, TERRAIN_Y + 3.6, FARM[1] + 5.4], look: [FARM[0], TERRAIN_Y + 0.2, FARM[1]] },
];

function Earth() {
  const geometry = useMemo(() => {
    const g = new THREE.IcosahedronGeometry(6, 3).toNonIndexed();
    const position = g.getAttribute("position");
    const colors: number[] = [];
    const ocean = new THREE.Color("#2F6E9E");
    const land = new THREE.Color("#5FA052");
    const dry = new THREE.Color("#C9A86A");
    const ice = new THREE.Color("#F2F5F7");
    const v = new THREE.Vector3();
    for (let i = 0; i < position.count; i += 3) {
      v.fromBufferAttribute(position, i).normalize();
      const n = Math.sin(v.x * 5.1) + Math.cos(v.y * 4.3 + v.z * 3.7) + Math.sin(v.z * 6.2);
      const color = Math.abs(v.y) > 0.86 ? ice : n > 0.9 ? dry : n > 0.15 ? land : ocean;
      for (let k = 0; k < 3; k++) colors.push(color.r, color.g, color.b);
    }
    g.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    return g;
  }, []);
  const ref = useRef<THREE.Mesh>(null);
  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.y += dt * 0.08;
  });
  return (
    <mesh ref={ref} geometry={geometry} rotation={[0.35, 0, 0]}>
      <meshStandardMaterial vertexColors flatShading roughness={0.9} />
    </mesh>
  );
}

function Terrain() {
  const geometry = useMemo(() => {
    const g = new THREE.PlaneGeometry(60, 60, 40, 40);
    g.rotateX(-Math.PI / 2);
    const position = g.getAttribute("position");
    for (let i = 0; i < position.count; i++) position.setY(i, height(position.getX(i), position.getZ(i)));
    const flat = g.toNonIndexed();
    const p = flat.getAttribute("position");
    const colors: number[] = [];
    const low = new THREE.Color("#7FB04A");
    const mid = new THREE.Color("#4E7F35");
    const high = new THREE.Color("#8C7A5B");
    const snow = new THREE.Color("#E8ECEF");
    for (let i = 0; i < p.count; i += 3) {
      const y = (p.getY(i) + p.getY(i + 1) + p.getY(i + 2)) / 3;
      const color = y > 5 ? snow : y > 3 ? high : y > 1 ? mid : low;
      for (let k = 0; k < 3; k++) colors.push(color.r, color.g, color.b);
    }
    flat.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    flat.computeVertexNormals();
    return flat;
  }, []);
  return (
    <mesh geometry={geometry} position={[0, TERRAIN_Y, 0]}>
      <meshStandardMaterial vertexColors flatShading roughness={1} />
    </mesh>
  );
}

/** El contorno de «su municipio»: un hexágono naranja sobre el relieve. */
function Municipality({ progress }: { progress: MutableRefObject<number> }) {
  // Solo se ve en la región y el municipio: en la finca, la línea pasaría delante de la cámara.
  const line = useRef<THREE.LineLoop>(null);
  useFrame(() => {
    if (line.current) line.current.visible = progress.current > 0.6 && progress.current < 2.5;
  });
  const points = useMemo(() => {
    const out: THREE.Vector3[] = [];
    for (let i = 0; i <= 6; i++) {
      const a = (i / 6) * Math.PI * 2;
      const x = FARM[0] + Math.cos(a) * 5;
      const z = FARM[1] + Math.sin(a) * 4;
      out.push(new THREE.Vector3(x, TERRAIN_Y + height(x, z) + 0.25, z));
    }
    return new THREE.BufferGeometry().setFromPoints(out);
  }, []);
  return (
    <lineLoop ref={line} geometry={points}>
      <lineBasicMaterial color="#F28C4A" />
    </lineLoop>
  );
}

/** La finca: la casa, el lote con sus camas, una cerca y dos árboles. */
function Farm() {
  const [x, z] = FARM;
  const y = TERRAIN_Y;
  return (
    <group position={[x, y, z]}>
      <mesh position={[-1.1, 0.3, -0.6]}>
        <boxGeometry args={[0.8, 0.6, 0.6]} />
        <meshStandardMaterial color="#F2E6CF" flatShading />
      </mesh>
      <mesh position={[-1.1, 0.8, -0.6]} rotation={[0, Math.PI / 4, 0]}>
        <coneGeometry args={[0.65, 0.45, 4]} />
        <meshStandardMaterial color="#C0533A" flatShading />
      </mesh>
      {[
        [0.2, 0.2],
        [0.9, 0.2],
        [0.2, 0.9],
        [0.9, 0.9],
      ].map(([bx, bz]) => (
        <group key={`${bx}-${bz}`} position={[bx, 0.08, bz]}>
          <mesh>
            <boxGeometry args={[0.6, 0.16, 0.6]} />
            <meshStandardMaterial color="#6B4A2E" flatShading />
          </mesh>
          {[-0.18, 0, 0.18].map((row) => (
            <mesh key={row} position={[row, 0.13, 0]}>
              <boxGeometry args={[0.06, 0.1, 0.5]} />
              <meshStandardMaterial color="#7FB04A" flatShading />
            </mesh>
          ))}
        </group>
      ))}
      {[
        [-0.3, 1.6],
        [1.7, -0.5],
      ].map(([tx, tz]) => (
        <group key={`${tx}-${tz}`} position={[tx, 0, tz]}>
          <mesh position={[0, 0.2, 0]}>
            <cylinderGeometry args={[0.05, 0.07, 0.4, 5]} />
            <meshStandardMaterial color="#6B4A2E" flatShading />
          </mesh>
          <mesh position={[0, 0.6, 0]}>
            <coneGeometry args={[0.3, 0.6, 6]} />
            <meshStandardMaterial color="#4E7F35" flatShading />
          </mesh>
        </group>
      ))}
    </group>
  );
}

const lerp3 = (a: THREE.Vector3Tuple, b: THREE.Vector3Tuple, t: number) =>
  new THREE.Vector3(THREE.MathUtils.lerp(a[0], b[0], t), THREE.MathUtils.lerp(a[1], b[1], t), THREE.MathUtils.lerp(a[2], b[2], t));

/** Mueve la cámara según el avance, con suavidad, y la mascota a su lado. */
function Rig({ progress }: { progress: MutableRefObject<number> }) {
  const current = useRef(progress.current);
  const look = useRef(new THREE.Vector3());
  const mascot = useRef<THREE.Group>(null);
  const fog = useRef<THREE.FogExp2>(null);
  const sky = useRef<THREE.Color>(null);
  const night = useMemo(() => new THREE.Color("#0B1226"), []);
  const day = useMemo(() => new THREE.Color("#9CC9E6"), []);
  useFrame(({ camera, size }, dt) => {
    // En una pantalla angosta la cámara se aleja, para que la escena quepa a lo ancho.
    const aspect = size.width / Math.max(size.height, 1);
    const away = aspect < 1 ? Math.min(1.8, 0.8 / aspect) : 1;
    current.current += (progress.current - current.current) * Math.min(1, dt * 3);
    const p = THREE.MathUtils.clamp(current.current, 0, KEYS.length - 1);
    const i = Math.min(Math.floor(p), KEYS.length - 2);
    const t = THREE.MathUtils.smootherstep(p - i, 0, 1);
    look.current.copy(lerp3(KEYS[i].look, KEYS[i + 1].look, t));
    camera.position
      .copy(lerp3(KEYS[i].pos, KEYS[i + 1].pos, t))
      .sub(look.current)
      .multiplyScalar(away)
      .add(look.current);
    camera.lookAt(look.current);
    // Entre la órbita y la región se cruza una capa de nubes: la niebla sube en medio del paso y tapa el corte.
    const cloud = p < 1 ? Math.sin(Math.PI * p) : 0;
    if (fog.current) fog.current.density = 0.004 + cloud * 0.25;
    // Del espacio oscuro al cielo de día al bajar.
    sky.current?.copy(night).lerp(day, THREE.MathUtils.clamp(p, 0, 1));
    // La mascota vuela delante de la cámara, a la derecha.
    if (mascot.current) {
      const offset = new THREE.Vector3(aspect < 1 ? 0.5 : 1.8, aspect < 1 ? -1.3 : 0.3, -4).applyQuaternion(camera.quaternion);
      mascot.current.position.copy(camera.position).add(offset);
      mascot.current.quaternion.copy(camera.quaternion);
      // En el celular, más chica y abajo, donde no la tapa la tarjeta.
      mascot.current.scale.setScalar(aspect < 1 ? 0.7 : 1);
    }
  });
  return (
    <>
      <color ref={sky} attach="background" args={["#0B1226"]} />
      <fogExp2 ref={fog} attach="fog" args={["#EEF4F7", 0]} />
      <group ref={mascot}>
        <Mascot3D scale={0.45} rotation={[0, -0.5, 0]} />
      </group>
    </>
  );
}

export default function JourneyCanvas({ progress }: { progress: MutableRefObject<number> }) {
  // Con la pestaña oculta no se dibuja nada.
  const [visible, setVisible] = useState(() => document.visibilityState !== "hidden");
  useEffect(() => {
    const sync = () => setVisible(document.visibilityState !== "hidden");
    document.addEventListener("visibilitychange", sync);
    return () => document.removeEventListener("visibilitychange", sync);
  }, []);
  return (
    <Canvas
      aria-hidden="true"
      dpr={[1, 1.5]}
      frameloop={visible ? "always" : "never"}
      camera={{ fov: 50, near: 0.1, far: 400, position: KEYS[0].pos }}
      gl={{ antialias: true, powerPreference: "low-power" }}
    >
      <hemisphereLight args={["#FFF6E0", "#2F4A2A", 1.1]} />
      <directionalLight position={[10, 20, 10]} intensity={1.6} />
      <Earth />
      <Terrain />
      <Municipality progress={progress} />
      <Farm />
      <Rig progress={progress} />
    </Canvas>
  );
}
