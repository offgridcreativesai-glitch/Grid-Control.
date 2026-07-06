import { useMemo, useRef } from "react"
import { Canvas, useFrame } from "@react-three/fiber"
import * as THREE from "three"
import { cn } from "@/lib/utils"

const vertexShader = /* glsl */ `
uniform float uTime;
varying vec3 vN;
varying vec3 vView;
varying vec3 vPos;

vec3 mod289(vec3 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 mod289(vec4 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 permute(vec4 x){return mod289(((x*34.0)+1.0)*x);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-0.85373472095314*r;}
float snoise(vec3 v){
  const vec2 C=vec2(1.0/6.0,1.0/3.0); const vec4 D=vec4(0.0,0.5,1.0,2.0);
  vec3 i=floor(v+dot(v,C.yyy)); vec3 x0=v-i+dot(i,C.xxx);
  vec3 g=step(x0.yzx,x0.xyz); vec3 l=1.0-g; vec3 i1=min(g.xyz,l.zxy); vec3 i2=max(g.xyz,l.zxy);
  vec3 x1=x0-i1+C.xxx; vec3 x2=x0-i2+C.yyy; vec3 x3=x0-D.yyy;
  i=mod289(i);
  vec4 p=permute(permute(permute(i.z+vec4(0.0,i1.z,i2.z,1.0))+i.y+vec4(0.0,i1.y,i2.y,1.0))+i.x+vec4(0.0,i1.x,i2.x,1.0));
  float n_=0.142857142857; vec3 ns=n_*D.wyz-D.xzx;
  vec4 j=p-49.0*floor(p*ns.z*ns.z);
  vec4 x_=floor(j*ns.z); vec4 y_=floor(j-7.0*x_);
  vec4 x=x_*ns.x+ns.yyyy; vec4 y=y_*ns.x+ns.yyyy; vec4 h=1.0-abs(x)-abs(y);
  vec4 b0=vec4(x.xy,y.xy); vec4 b1=vec4(x.zw,y.zw);
  vec4 s0=floor(b0)*2.0+1.0; vec4 s1=floor(b1)*2.0+1.0; vec4 sh=-step(h,vec4(0.0));
  vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy; vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
  vec3 p0=vec3(a0.xy,h.x); vec3 p1=vec3(a0.zw,h.y); vec3 p2=vec3(a1.xy,h.z); vec3 p3=vec3(a1.zw,h.w);
  vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));
  p0*=norm.x;p1*=norm.y;p2*=norm.z;p3*=norm.w;
  vec4 m=max(0.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.0); m=m*m;
  return 42.0*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));
}

void main(){
  vN = normalize(normalMatrix * normal);
  float n = snoise(normal * 1.5 + uTime * 0.22);
  float n2 = snoise(normal * 3.0 - uTime * 0.35);
  vec3 disp = position + normal * (n * 0.20 + n2 * 0.08);
  vec4 mv = modelViewMatrix * vec4(disp, 1.0);
  vView = normalize(-mv.xyz);
  vPos = disp;
  gl_Position = projectionMatrix * mv;
}
`

const fragmentShader = /* glsl */ `
uniform float uTime;
uniform vec3 uA;
uniform vec3 uB;
uniform vec3 uC;
varying vec3 vN;
varying vec3 vView;
varying vec3 vPos;

void main(){
  float facing = clamp(dot(normalize(vN), normalize(vView)), 0.0, 1.0);
  // bright toward the camera, transparent at the rim -> the orb melts into the bloom
  float core = pow(facing, 1.6);
  float swirl  = sin(vPos.x * 2.4 + uTime) * 0.5 + 0.5;
  float swirl2 = sin(vPos.y * 3.1 - uTime * 1.25 + vPos.z * 2.2) * 0.5 + 0.5;
  vec3 col = mix(uA, uB, swirl);
  col = mix(col, uC, swirl2 * 0.55);
  col += uC * pow(facing, 5.0) * 1.2;          // hot lava center
  float alpha = core * 0.92;
  gl_FragColor = vec4(col * 1.25, alpha);
}
`

function Plasma() {
  const ref = useRef<THREE.Mesh>(null)
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader,
        fragmentShader,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        side: THREE.FrontSide,
        uniforms: {
          uTime: { value: 0 },
          uA: { value: new THREE.Color("#5b3df0") },
          uB: { value: new THREE.Color("#2E6BFF") },
          uC: { value: new THREE.Color("#FF4D00") },
        },
      }),
    [],
  )
  useFrame((s) => {
    material.uniforms.uTime.value = s.clock.elapsedTime
    if (ref.current) ref.current.rotation.y = s.clock.elapsedTime * 0.14
  })
  return (
    <mesh ref={ref} scale={1.5}>
      <icosahedronGeometry args={[1, 40]} />
      <primitive object={material} attach="material" />
    </mesh>
  )
}

/** Soul-core energy orb — a churning fresnel plasma that has no hard edge; it dissolves into its own glow. */
export function EnergyOrb({ className }: { className?: string }) {
  return (
    <div className={cn("relative", className)}>
      {/* bloom halo behind the canvas — the orb bleeds into this */}
      <div
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(46% 46% at 50% 50%, rgba(91,61,240,0.55), transparent 64%)," +
            "radial-gradient(34% 34% at 58% 44%, rgba(255,77,0,0.38), transparent 62%)," +
            "radial-gradient(40% 40% at 42% 58%, rgba(46,107,255,0.34), transparent 62%)",
          filter: "blur(26px)",
        }}
      />
      <Canvas camera={{ position: [0, 0, 4.2], fov: 50 }} dpr={[1, 1.8]} gl={{ alpha: true, antialias: true }}>
        <Plasma />
      </Canvas>
    </div>
  )
}
