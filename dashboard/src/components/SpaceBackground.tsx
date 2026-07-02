import { useMemo, useRef } from "react"
import { Canvas, useFrame } from "@react-three/fiber"
import * as THREE from "three"
import { cn } from "@/lib/utils"

function Stars({ count = 1600 }: { count?: number }) {
  const ref = useRef<THREE.Points>(null)
  const positions = useMemo(() => {
    const a = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const r = 6 + Math.random() * 20
      const t = Math.random() * Math.PI * 2
      const p = Math.acos(2 * Math.random() - 1)
      a[i * 3] = r * Math.sin(p) * Math.cos(t)
      a[i * 3 + 1] = r * Math.sin(p) * Math.sin(t)
      a[i * 3 + 2] = r * Math.cos(p)
    }
    return a
  }, [count])

  useFrame((_, dt) => {
    if (ref.current) {
      ref.current.rotation.y += dt * 0.012
      ref.current.rotation.x += dt * 0.004
    }
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.06}
        sizeAttenuation
        transparent
        opacity={0.85}
        color="#aeb8ff"
        depthWrite={false}
      />
    </points>
  )
}

function Drift() {
  useFrame((s) => {
    const t = s.clock.elapsedTime
    s.camera.position.x = Math.sin(t * 0.05) * 0.7
    s.camera.position.y = Math.cos(t * 0.04) * 0.45
    s.camera.lookAt(0, 0, 0)
  })
  return null
}

/** Shared deep-space backdrop: nebula bleed (CSS) + drifting particle field (Three.js). */
export function SpaceBackground({ className }: { className?: string }) {
  return (
    <div className={cn("fixed inset-0 -z-10 overflow-hidden", className)} style={{ background: "#0A0C0B" }}>
      {/* nebula color bleed at the edges */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(60% 50% at 80% 22%, rgba(46,107,255,0.18), transparent 70%)," +
            "radial-gradient(55% 45% at 18% 78%, rgba(120,70,255,0.16), transparent 70%)," +
            "radial-gradient(50% 42% at 55% 55%, rgba(255,77,0,0.05), transparent 72%)",
        }}
      />
      <Canvas camera={{ position: [0, 0, 12], fov: 60 }} dpr={[1, 1.6]} gl={{ alpha: true, antialias: true }}>
        <Stars />
        <Drift />
      </Canvas>
    </div>
  )
}
