import { useEffect, useMemo } from "react";
import { CanvasTexture, SRGBColorSpace } from "three";

interface LabelProps {
  text: string;
  position: readonly [number, number, number];
}

// Texture pixels per text line, and the label's height in scene units.
const textPixels = 40;
const paddingPixels = 12;
const labelHeight = 0.9;

function readToken(name: string): string {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
}

// Draws the text once onto a canvas: a sprite needs no extra React root per
// label (unlike drei's Html) and nothing is fetched (unlike drei's Text).
function createLabelTexture(text: string): {
  texture: CanvasTexture;
  aspect: number;
} {
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");
  const font = `500 ${String(textPixels)}px ${readToken("--font-ibm-plex-mono") || "monospace"}`;
  if (context) {
    context.font = font;
  }
  const textWidth = context ? context.measureText(text).width : text.length;
  canvas.width = Math.ceil(textWidth + paddingPixels * 2);
  canvas.height = textPixels + paddingPixels * 2;
  if (context) {
    // Resizing the canvas resets its state, so the font is set again.
    context.font = font;
    context.fillStyle = readToken("--color-background");
    context.globalAlpha = 0.75;
    context.beginPath();
    context.roundRect(0, 0, canvas.width, canvas.height, 10);
    context.fill();
    context.globalAlpha = 1;
    context.fillStyle = readToken("--color-text");
    context.textBaseline = "middle";
    context.fillText(text, paddingPixels, canvas.height / 2);
  }
  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  return { texture, aspect: canvas.width / canvas.height };
}

// A text label pinned to a scene position that always faces the camera and
// never intercepts the pointer.
export function Label({ text, position }: LabelProps) {
  const { texture, aspect } = useMemo(() => createLabelTexture(text), [text]);

  useEffect(
    () => () => {
      texture.dispose();
    },
    [texture],
  );

  return (
    <sprite
      position={[position[0], position[1], position[2]]}
      scale={[labelHeight * aspect, labelHeight, 1]}
      raycast={() => null}
      renderOrder={10}
    >
      <spriteMaterial map={texture} transparent depthTest={false} />
    </sprite>
  );
}
