import { useRef, useMemo } from "react"
import { Canvas, useFrame } from "@react-three/fiber"
import { Line, MeshDistortMaterial } from "@react-three/drei"
import * as THREE from "three"

type Node = { name: string; color: string; lead?: boolean; pos: [number, number, number] }

// Atlas at the centre (the one you talk to), the crew softly orbiting.
const NODES: Node[] = [
  { name: "Atlas", color: "#FF4D00", lead: true, pos: [0, 0, 0] },
  { name: "Scout", color: "#16A07E", pos: [2.7, 1.2, -0.6] },
  { name: "Cadence", color: "#1FA98C", pos: [-2.9, 0.9, 0.4] },
  { name: "Riveter", color: "#2A6E66", pos: [2.0, -1.7, 0.8] },
  { name: "Lumen", color: "#FF6A2B", pos: [-2.2, -1.5, -0.7] },
  { name: "Gauge", color: "#2A8E80", pos: [3.2, -0.3, 0.9] },
  { name: "Echo", color: "#16A07E", pos: [-3.3, -0.2, -0.3] },
  { name: "Sentry", color: "#1F8E78", pos: [0.6, 2.2, -1.0] },
  { name: "Finch", color: "#2A8E80", pos: [-0.7, -2.4, 0.6] },
]

function CrewOrb({ node }: { node: Node }) {
  const ref = useRef<THREE.Mesh>(null!)
  const phase = useMemo(() => Math.random() * Math.PI * 2, [])
  useFrame(({ clock }) => {
    const t = clock.elapsedTime
    ref.current.position.y = node.pos[1] + Math.sin(t * 0.7 + phase) * 0.12
    ref.current.scale.setScalar(0.46 + Math.sin(t * 1.1 + phase) * 0.02)
  })
  return (
    <mesh ref={ref} position={node.pos}>
      <sphereGeometry args={[1, 48, 48]} />
      <meshStandardMaterial
        color={node.color}
        emissive={node.color}
        emissiveIntensity={0.22}
        roughness={0.55}
        metalness={0.05}
      />
    </mesh>
  )
}

function AtlasOrb() {
  const ref = useRef<THREE.Mesh>(null!)
  useFrame(({ clock }) => {
    const t = clock.elapsedTime
    ref.current.scale.setScalar(1.05 + Math.sin(t * 1.4) * 0.04)
  })
  return (
    <mesh ref={ref}>
      <sphereGeometry args={[1, 96, 96]} />
      <MeshDistortMaterial
        color="#FF4D00"
        emissive="#FF4D00"
        emissiveIntensity={0.35}
        roughness={0.4}
        metalness={0.1}
        distort={0.3}
        speed={1.6}
      />
    </mesh>
  )
}

function Scene({ pointer }: { pointer: React.MutableRefObject<{ x: number; y: number }> }) {
  const group = useRef<THREE.Group>(null!)
  useFrame(({ clock }) => {
    const t = clock.elapsedTime
    group.current.rotation.y = t * 0.06 + pointer.current.x * 0.3
    group.current.rotation.x = THREE.MathUtils.lerp(
      group.current.rotation.x,
      pointer.current.y * 0.2,
      0.05,
    )
  })

  const lines = useMemo(() => {
    const atlas = NODES[0].pos
    return NODES.slice(1).map((n) => [atlas, n.pos] as [number, number, number][])
  }, [])

  return (
    <group ref={group}>
      {lines.map((pts, i) => (
        <Line key={i} points={pts} color="#FF8A5C" lineWidth={0.8} transparent opacity={0.2} />
      ))}
      <AtlasOrb />
      {NODES.slice(1).map((n) => (
        <CrewOrb key={n.name} node={n} />
      ))}
    </group>
  )
}

export function TeamConstellation() {
  const pointer = useRef({ x: 0, y: 0 })
  return (
    <Canvas
      camera={{ position: [0, 0, 9], fov: 42 }}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true }}
      onPointerMove={(e) => {
        pointer.current.x = (e.clientX / window.innerWidth) * 2 - 1
        pointer.current.y = -((e.clientY / window.innerHeight) * 2 - 1)
      }}
      style={{ background: "transparent" }}
    >
      <ambientLight intensity={0.6} />
      <pointLight position={[7, 7, 9]} intensity={1.6} color="#fff3e8" />
      <pointLight position={[-7, -5, 3]} intensity={0.7} color="#16A07E" />
      <directionalLight position={[-4, 6, 5]} intensity={0.5} color="#ffd9be" />
      <Scene pointer={pointer} />
    </Canvas>
  )
}
