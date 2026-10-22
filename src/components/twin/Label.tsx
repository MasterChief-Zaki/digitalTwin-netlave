import { Html } from "@react-three/drei";
import styles from "./Label.module.scss";

interface LabelProps {
  text: string;
  position: readonly [number, number, number];
}

// An HTML label pinned to a scene position; it never intercepts the pointer.
export function Label({ text, position }: LabelProps) {
  return (
    <Html
      position={[position[0], position[1], position[2]]}
      center
      pointerEvents="none"
      zIndexRange={[10, 0]}
    >
      <span className={styles.label}>{text}</span>
    </Html>
  );
}
