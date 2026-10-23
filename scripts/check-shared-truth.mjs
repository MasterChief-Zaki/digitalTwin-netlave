import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";

const root = new URL("../", import.meta.url);
const siblingNames = ["netlave", "landing-netlave", "digitalTwin-netlave"];
const files = [
  "src/content/ground-truth.json",
  "src/styles/fonts.ts",
  "public/brand/source.png",
  "public/brand/mark.png",
  "public/brand/logo-light.png",
  "public/brand/social.png",
  "src/app/favicon.ico",
  "src/app/icon.png",
  "src/app/apple-icon.png",
  "src/app/ground-truth/page.tsx",
  "src/app/ground-truth/page.module.scss",
  "public/llms.txt",
];
const truth = JSON.parse(await readFile(new URL(files[0], root), "utf8"));
assert.equal(truth.brand, "NetLave");
assert.equal(
  truth.siteAssumptions.forestAreaHa,
  truth.zones.reduce((sum, zone) => sum + zone.areaHa, 0),
);
assert.equal(truth.scenarios.length, 4);
assert.match(truth.source.commit, /^[a-f0-9]{40}$/);
const favicon = await readFile(new URL("src/app/favicon.ico", root));
assert.equal(favicon.readUInt16LE(2), 1);
assert.equal(favicon.readUInt16LE(4), 3);
for (const [index, size] of [16, 32, 48].entries())
  assert.equal(favicon[6 + index * 16], size);

if (process.argv.includes("--siblings")) {
  for (const file of files) {
    const normalize = (contents) =>
      /\.(json|ts|tsx|scss|txt)$/.test(file)
        ? contents.toString("utf8").replace(/\r\n/g, "\n")
        : contents;
    const expected = createHash("sha256")
      .update(normalize(await readFile(new URL(file, root))))
      .digest("hex");
    for (const name of siblingNames) {
      const location = new URL(`../${name}/${file}`, root);
      const actual = createHash("sha256")
        .update(normalize(await readFile(location)))
        .digest("hex");
      assert.equal(actual, expected, `${fileURLToPath(location)} differs`);
    }
  }
  console.log(
    "All three repositories have identical shared facts, fonts, brand assets and references.",
  );
} else {
  console.log(
    "Shared facts and favicon structure are valid. Use --siblings to compare all three repos.",
  );
}
