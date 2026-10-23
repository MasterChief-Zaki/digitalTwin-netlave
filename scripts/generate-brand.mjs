import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

// Use the image tooling already installed with Next.js; no extra dependency.
const require = createRequire(import.meta.url);
const sharp = createRequire(require.resolve("next/package.json"))("sharp");
const root = new URL("../", import.meta.url);
const source = fileURLToPath(new URL("public/brand/source.png", root));
const brand = new URL("public/brand/", root);
const app = new URL("src/app/", root);
await mkdir(brand, { recursive: true });

// Crop the supplied artwork, not a redrawn approximation. The upper panel
// contains the dark monogram; the lower panel contains the pale full lockup.
const mark = await sharp(source)
  .extract({ left: 535, top: 141, width: 475, height: 524 })
  .extend({ top: 38, bottom: 38, left: 62, right: 63, background: "#f1fcfc" })
  .png()
  .toBuffer();
await writeFile(new URL("mark.png", brand), mark);

const { data: pixels, info } = await sharp(source)
  .extract({ left: 535, top: 1131, width: 475, height: 691 })
  .ensureAlpha()
  .raw()
  .toBuffer({ resolveWithObject: true });
// Remove only the flat purple background, preserving antialiased edges.
for (let offset = 0; offset < pixels.length; offset += 4) {
  const coverage = Math.max(0, Math.min(1, (pixels[offset + 1] - 4) / 248));
  pixels[offset] = 241;
  pixels[offset + 1] = 252;
  pixels[offset + 2] = 252;
  pixels[offset + 3] = Math.round(coverage * 255);
}
await sharp(pixels, { raw: info })
  .png()
  .toFile(fileURLToPath(new URL("logo-light.png", brand)));
await sharp(mark)
  .resize(192, 192)
  .png()
  .toFile(fileURLToPath(new URL("icon.png", app)));
await sharp(mark)
  .resize(180, 180)
  .png()
  .toFile(fileURLToPath(new URL("apple-icon.png", app)));

// ICO directory with PNG payloads at the common browser sizes.
const sizes = [16, 32, 48];
const frames = await Promise.all(
  sizes.map((size) => sharp(mark).resize(size, size).png().toBuffer()),
);
const header = Buffer.alloc(6 + sizes.length * 16);
header.writeUInt16LE(1, 2);
header.writeUInt16LE(sizes.length, 4);
let payloadOffset = header.length;
frames.forEach((frame, index) => {
  const entry = 6 + index * 16;
  header[entry] = sizes[index];
  header[entry + 1] = sizes[index];
  header.writeUInt16LE(1, entry + 4);
  header.writeUInt16LE(32, entry + 6);
  header.writeUInt32LE(frame.length, entry + 8);
  header.writeUInt32LE(payloadOffset, entry + 12);
  payloadOffset += frame.length;
});
await writeFile(
  new URL("favicon.ico", app),
  Buffer.concat([header, ...frames]),
);
console.log("Generated NetLave logo crops, favicon and touch icons.");
