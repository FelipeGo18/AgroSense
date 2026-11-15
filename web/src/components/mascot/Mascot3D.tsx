import { useFrame, type ThreeElements } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

/**
 * La Semilla Sputnik en 3D low-poly (HU-171): la misma mascota de `Mascot.tsx`, hecha con pocas caras y sombreado
 * plano para el recorrido del satélite a la finca (HU-155).
 *
 * Partes, con su punto de giro (el mismo de las clases de la versión 2D):
 * - `body`: la semilla, gira en su centro.
 * - `sprout`: el brote con sus dos hojas-panel, gira en la punta de la semilla.
 * - `arm-left` y `arm-right`: los brazos de manguera, giran en el hombro.
 * - `roots`: las raíces-antena, giran bajo la semilla.
 * - `eyes`: los ojos de pastel, parpadean escalando en Y.
 *
 * Solo se dibuja con movimiento (quien la usa pregunta `useAnimated()`): en modo ligero se usa la mascota 2D quieta.
 */

const INK = "#1D1D1B";
const CREAM = "#FFF6E0";
const SEED = "#C8873A";
const SEED_LIGHT = "#E3AE68";
const LEAF = "#5FA052";
const LEAF_LIGHT = "#8CC56A";
const HOSE = "#E76F51";

function flat(color: string) {
  return new THREE.MeshStandardMaterial({ color, flatShading: true, roughness: 0.85 });
}

/** Un tubo entre dos puntos: brazos de manguera y raíces. */
function Tube({ from, to, radius, color }: { from: THREE.Vector3Tuple; to: THREE.Vector3Tuple; radius: number; color: string }) {
  const { position, quaternion, length } = useMemo(() => {
    const a = new THREE.Vector3(...from);
    const b = new THREE.Vector3(...to);
    const dir = b.clone().sub(a);
    return {
      position: a.clone().add(b).multiplyScalar(0.5),
      quaternion: new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize()),
      length: dir.length(),
    };
  }, [from, to]);
  const material = useMemo(() => flat(color), [color]);
  return (
    <mesh position={position} quaternion={quaternion} material={material}>
      <cylinderGeometry args={[radius, radius, length, 6]} />
    </mesh>
  );
}

export function Mascot3D({ waving = true, ...props }: { waving?: boolean } & ThreeElements["group"]) {
  const body = useRef<THREE.Group>(null);
  const armRight = useRef<THREE.Group>(null);
  const sprout = useRef<THREE.Group>(null);
  const eyes = useRef<THREE.Group>(null);
  const materials = useMemo(
    () => ({
      seed: flat(SEED),
      seedLight: flat(SEED_LIGHT),
      leaf: flat(LEAF),
      leafLight: flat(LEAF_LIGHT),
      cream: flat(CREAM),
      ink: flat(INK),
    }),
    [],
  );

  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    if (body.current) body.current.position.y = Math.sin(t * 1.6) * 0.06;
    if (sprout.current) sprout.current.rotation.z = Math.sin(t * 2.2) * 0.12;
    if (armRight.current) armRight.current.rotation.z = waving ? -1.1 + Math.sin(t * 6) * 0.35 : -0.3;
    // Parpadeo: cada 4 s los ojos se cierran un instante.
    if (eyes.current) eyes.current.scale.y = t % 4 < 0.12 ? 0.1 : 1;
  });

  return (
    <group {...props}>
      <group ref={body} name="body">
        {/* La semilla: un icosaedro estirado, con una mancha clara al frente. */}
        <mesh material={materials.seed} scale={[0.9, 1.05, 0.8]}>
          <icosahedronGeometry args={[1, 1]} />
        </mesh>
        <mesh material={materials.seedLight} position={[-0.25, 0.3, 0.55]} scale={[0.35, 0.3, 0.2]}>
          <icosahedronGeometry args={[1, 0]} />
        </mesh>

        {/* Los ojos de pastel: blanco con una cuña negra. */}
        <group ref={eyes} name="eyes" position={[0, 0.15, 0.72]}>
          {[-0.28, 0.28].map((x) => (
            <group key={x} position={[x, 0, 0]}>
              <mesh material={materials.cream} scale={[0.22, 0.26, 0.08]}>
                <icosahedronGeometry args={[1, 1]} />
              </mesh>
              <mesh material={materials.ink} position={[0.04, -0.03, 0.07]} scale={[0.11, 0.14, 0.04]}>
                <icosahedronGeometry args={[1, 0]} />
              </mesh>
            </group>
          ))}
        </group>
        {/* La sonrisa. */}
        <mesh material={materials.ink} position={[0, -0.25, 0.72]} rotation={[0, 0, Math.PI]}>
          <torusGeometry args={[0.16, 0.03, 4, 8, Math.PI]} />
        </mesh>

        {/* El brote: la antena de señal con dos hojas-panel. */}
        <group ref={sprout} name="sprout" position={[0, 1.0, 0]}>
          <Tube from={[0, 0, 0]} to={[0, 0.55, 0]} radius={0.05} color={LEAF} />
          <mesh material={materials.leaf} position={[-0.28, 0.55, 0]} rotation={[0, 0, 0.6]} scale={[0.32, 0.14, 0.05]}>
            <octahedronGeometry args={[1, 0]} />
          </mesh>
          <mesh material={materials.leafLight} position={[0.28, 0.6, 0]} rotation={[0, 0, -0.6]} scale={[0.32, 0.14, 0.05]}>
            <octahedronGeometry args={[1, 0]} />
          </mesh>
        </group>

        {/* Los brazos de manguera: el izquierdo abajo, el derecho saluda. */}
        <group name="arm-left" position={[-0.85, -0.05, 0]} rotation={[0, 0, 0.4]}>
          <Tube from={[0, 0, 0]} to={[-0.45, -0.35, 0.1]} radius={0.07} color={HOSE} />
          <mesh material={materials.cream} position={[-0.47, -0.37, 0.1]} scale={0.13}>
            <icosahedronGeometry args={[1, 0]} />
          </mesh>
        </group>
        <group ref={armRight} name="arm-right" position={[0.85, -0.05, 0]}>
          <Tube from={[0, 0, 0]} to={[0.5, 0.25, 0.1]} radius={0.07} color={HOSE} />
          <mesh material={materials.cream} position={[0.52, 0.27, 0.1]} scale={0.13}>
            <icosahedronGeometry args={[1, 0]} />
          </mesh>
        </group>

        {/* Las raíces: tres antenas barridas hacia atrás. */}
        <group name="roots" position={[0, -0.95, -0.1]}>
          {[-0.35, 0, 0.35].map((x) => (
            <Tube key={x} from={[x * 0.4, 0, 0]} to={[x, -0.55, -0.45]} radius={0.035} color={INK} />
          ))}
        </group>
      </group>
    </group>
  );
}
