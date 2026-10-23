import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import vm from "node:vm";
import { pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const entry = require.resolve("@react-three/fiber/package.json");
const packageRoot = new URL("./", pathToFileURL(entry));
const timerSource = (
  await readFile(
    new URL("../src/core/Timer.js", pathToFileURL(require.resolve("three"))),
    "utf8",
  )
).replace("export { Timer };", "");
let nowMs = 1000;
const performance = { now: () => nowMs };
for (const file of [
  "events-e51d7528.esm.js",
  "events-0dab3c53.cjs.dev.js",
  "events-98e95d43.cjs.prod.js",
]) {
  const source = await readFile(new URL(`dist/${file}`, packageRoot), "utf8");
  const helper = source.slice(
    source.indexOf("const createTimerClock ="),
    source.indexOf("const createStore ="),
  );
  assert.ok(helper.length > 0, `${file} must use the locked Timer patch`);
  const context = vm.createContext({ performance });
  const clock = vm.runInContext(
    `${timerSource}\nconst THREE = { Timer }; const THREE__namespace = { Timer };\n${helper}\ncreateTimerClock()`,
    context,
  );
  assert.equal(clock.getDelta(), 0);
  nowMs += 100;
  assert.equal(clock.getDelta(), 0.1);
  assert.equal(clock.elapsedTime, 0.1);
  nowMs += 200;
  assert.ok(Math.abs(clock.getElapsedTime() - 0.3) < 1e-12);
  clock.stop();
  assert.equal(clock.running, false);
  assert.equal(clock.getDelta(), 0);
  nowMs += 1000;
  clock.start();
  assert.equal(clock.elapsedTime, 0);
  nowMs += 100;
  assert.equal(clock.getDelta(), 0.1, "restart excludes time spent stopped");
  assert.equal(clock.running, true);
  clock.elapsedTime = 120;
  assert.equal(
    clock.elapsedTime,
    120,
    "manual advance retains a writable elapsed time",
  );
}
console.log(
  "Fiber Timer bridge passes start, stop, elapsed and manual-advance checks in every bundle.",
);
