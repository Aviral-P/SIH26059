"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Line } from "@react-three/drei";
import * as THREE from "three";
import { useRef } from "react";

function Globe() {
  const globeRef = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (globeRef.current) {
      globeRef.current.rotation.y += delta * 0.035;
    }
  });

  const icebergPoints = [
    [-0.75, -0.25, 0.62],
    [-0.45, -0.48, 0.72],
    [0.15, -0.62, 0.68],
    [0.48, -0.42, 0.58],
    [0.7, -0.15, 0.45],
  ];

  return (
    <group ref={globeRef} rotation={[0.25, 0, 0]}>
      {/* Earth */}
      <mesh>
        <sphereGeometry args={[1.45, 96, 96]} />
        <meshStandardMaterial
          color="#17232b"
          roughness={0.88}
          metalness={0.08}
        />
      </mesh>

      {/* Subtle atmosphere */}
      <mesh>
        <sphereGeometry args={[1.49, 64, 64]} />
        <meshBasicMaterial
          color="#78909c"
          transparent
          opacity={0.055}
          side={THREE.BackSide}
        />
      </mesh>

      {/* Latitude / longitude wireframe */}
      <mesh>
        <sphereGeometry args={[1.458, 24, 16]} />
        <meshBasicMaterial
          color="#71808a"
          wireframe
          transparent
          opacity={0.13}
        />
      </mesh>

      {/* Antarctic ice cap */}
      <mesh position={[0, -1.31, 0]} rotation={[0, 0, 0]}>
        <sphereGeometry args={[0.72, 64, 24, 0, Math.PI * 2, 0, 0.72]} />
        <meshStandardMaterial
          color="#dfe8e8"
          roughness={0.92}
          metalness={0}
        />
      </mesh>

      {/* Iceberg markers */}
      {icebergPoints.map((position, i) => (
        <mesh key={i} position={position as [number, number, number]}>
          <sphereGeometry args={[0.025, 12, 12]} />
          <meshBasicMaterial color="#e6edf0" />
        </mesh>
      ))}

      {/* Example iceberg trajectory */}
      <Line
        points={[
          [-0.75, -0.25, 0.62],
          [-0.62, -0.34, 0.66],
          [-0.45, -0.42, 0.69],
          [-0.25, -0.51, 0.71],
          [-0.05, -0.58, 0.7],
        ]}
        color="#aebcc2"
        lineWidth={1}
        transparent
        opacity={0.65}
      />

      {/* Vessel route */}
      <Line
        points={[
          [-1.05, -0.72, 0.18],
          [-0.82, -0.78, 0.3],
          [-0.55, -0.84, 0.38],
          [-0.25, -0.91, 0.43],
          [0.05, -0.97, 0.4],
        ]}
        color="#d8e1e3"
        lineWidth={1.4}
      />

      {/* Vessel */}
      <mesh position={[-1.05, -0.72, 0.18]}>
        <octahedronGeometry args={[0.045, 0]} />
        <meshBasicMaterial color="#f1f4f4" />
      </mesh>
    </group>
  );
}

export default function AntarcticGlobe() {
  return (
    <div className="absolute inset-0">
      <Canvas
        camera={{
          position: [0, 0.15, 3.65],
          fov: 42,
        }}
        dpr={[1, 2]}
      >
        <ambientLight intensity={0.7} />

        <directionalLight
          position={[3, 2, 4]}
          intensity={1.2}
        />

        <Globe />

        <OrbitControls
          enableZoom={false}
          enablePan={false}
          autoRotate={false}
          minPolarAngle={Math.PI * 0.25}
          maxPolarAngle={Math.PI * 0.75}
        />
      </Canvas>
    </div>
  );
}