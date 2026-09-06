"use client";

import { Canvas, useFrame, useLoader } from "@react-three/fiber";
import { useRef, useState } from "react";
import * as THREE from "three";

const EARTH_TEXTURE =
  "https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_atmos_2048.jpg";

const FACTS = [
  {
    label: "RESEARCH VESSELS",
    text: "A polar route is never truly static.",
  },
  {
    label: "MOVING ICEBERGS",
    text: "An iceberg is a moving hazard, not a fixed obstacle.",
  },
  {
    label: "SEA ICE",
    text: "The ice edge is a changing boundary.",
  },
  {
    label: "OCEAN CURRENTS",
    text: "The ocean can move ice long after it is observed.",
  },
  {
    label: "ATMOSPHERIC FORCING",
    text: "Wind changes the navigation picture.",
  },
  {
    label: "FORECASTING",
    text: "A trajectory is a prediction, not a promise.",
  },
  {
    label: "SATELLITE OBSERVATION",
    text: "The polar environment is observed from above.",
  },
  {
    label: "SAR",
    text: "Radar adds another view of the polar environment.",
  },
  {
    label: "DECISION SUPPORT",
    text: "The objective is not simply to find ice.",
  },
  {
    label: "SIH26059",
    text: "The warning should arrive before the hazard does.",
  },
];

function Earth({
  onFactChange,
}: {
  onFactChange: () => void;
}) {
  const earthRef = useRef<THREE.Mesh>(null);

  const texture = useLoader(THREE.TextureLoader, EARTH_TEXTURE);

  const [dragging, setDragging] = useState(false);

  const lastPointer = useRef({
    x: 0,
    y: 0,
  });

  const dragDistance = useRef(0);

  /*
   * Quaternion gives us true 3D rotation.
   * This prevents the Earth from behaving like
   * a flat horizontal/vertical slider.
   */
  const targetQuaternion = useRef(new THREE.Quaternion());

  const rotationQuaternion = useRef(new THREE.Quaternion());

  useFrame((_, delta) => {
    if (!earthRef.current) return;

    /*
     * Slow autonomous rotation when the user
     * is not interacting with the Earth.
     */
    if (!dragging) {
      const autoRotation = new THREE.Quaternion();

      autoRotation.setFromAxisAngle(
        new THREE.Vector3(0, 1, 0),
        delta * 0.04
      );

      targetQuaternion.current.multiply(autoRotation);
    }

    /*
     * Smoothly approach the target rotation.
     */
    rotationQuaternion.current.slerp(
      targetQuaternion.current,
      0.12
    );

    earthRef.current.quaternion.copy(
      rotationQuaternion.current
    );
  });

  return (
    <mesh
      ref={earthRef}
      position={[2.4, 0, 0]}
      scale={3.2}
      onPointerDown={(event) => {
        event.stopPropagation();

        setDragging(true);

        dragDistance.current = 0;

        lastPointer.current = {
          x: event.clientX,
          y: event.clientY,
        };

        /*
         * Start from the current orientation.
         */
        targetQuaternion.current.copy(
          earthRef.current?.quaternion ??
            new THREE.Quaternion()
        );
      }}
      onPointerMove={(event) => {
        if (!dragging) return;

        const dx =
          event.clientX - lastPointer.current.x;

        const dy =
          event.clientY - lastPointer.current.y;

        lastPointer.current = {
          x: event.clientX,
          y: event.clientY,
        };

        /*
         * Total movement controls when the next
         * fact appears.
         */
        dragDistance.current += Math.sqrt(
          dx * dx + dy * dy
        );

        /*
         * Convert mouse movement into a 3D
         * trackball rotation.
         *
         * Horizontal movement rotates around
         * the camera's Y axis.
         *
         * Vertical movement rotates around
         * the camera's X axis.
         *
         * Because these are quaternions, diagonal
         * movement naturally produces combined
         * 3D rotation.
         */
        const rotationX = new THREE.Quaternion();
        const rotationY = new THREE.Quaternion();

        rotationY.setFromAxisAngle(
          new THREE.Vector3(0, 1, 0),
          dx * 0.008
        );

        rotationX.setFromAxisAngle(
          new THREE.Vector3(1, 0, 0),
          dy * 0.008
        );

        /*
         * Apply both rotations to the current
         * orientation.
         */
        targetQuaternion.current
          .premultiply(rotationY)
          .premultiply(rotationX);

        /*
         * Reveal a new fact after meaningful
         * user interaction.
         */
        if (dragDistance.current >= 180) {
          dragDistance.current = 0;
          onFactChange();
        }
      }}
      onPointerUp={(event) => {
        event.stopPropagation();
        setDragging(false);
      }}
      onPointerCancel={() => {
        setDragging(false);
      }}
      onPointerLeave={() => {
        setDragging(false);
      }}
    >
      <sphereGeometry args={[1, 64, 64]} />

      <meshBasicMaterial map={texture} />
    </mesh>
  );
}

export default function AntarcticGlobe() {
  const [factIndex, setFactIndex] = useState(0);

  const currentFact = FACTS[factIndex];

  const nextFact = () => {
    setFactIndex(
      (current) => (current + 1) % FACTS.length
    );
  };

  return (
    <div className="relative h-full w-full overflow-hidden bg-black">
      <Canvas
        camera={{
          position: [0, 0, 6],
          fov: 45,
        }}
        style={{
          position: "absolute",
          inset: 0,
        }}
      >
        <Earth onFactChange={nextFact} />
      </Canvas>

      {/* Fact */}
      <div className="pointer-events-none absolute left-[7%] top-1/2 z-20 w-[36%] -translate-y-1/2 text-white">
        <p className="text-xs tracking-[0.3em] text-white/45">
          {currentFact.label}
        </p>

        <p
          key={factIndex}
          className="mt-6 max-w-[520px] font-serif text-4xl leading-[1.15] md:text-5xl lg:text-6xl"
        >
          {currentFact.text}
        </p>
      </div>

      {/* Interaction hint */}
      <div className="pointer-events-none absolute bottom-10 left-[7%] z-20">
        <p className="text-[10px] tracking-[0.2em] text-white/35">
          DRAG THE EARTH
        </p>
      </div>
    </div>
  );
}