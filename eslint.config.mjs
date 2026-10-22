import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";
import reactThree from "@react-three/eslint-plugin";
import prettierCompatibility from "eslint-config-prettier/flat";
import typescriptEslint from "typescript-eslint";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTypescript,
  // The plugin only ships legacy presets, so register it and reuse its recommended rules.
  {
    plugins: { "@react-three": reactThree },
    rules: reactThree.configs.recommended.rules,
  },
  // Strict, type-aware TypeScript rules; they read types through the project's tsconfig.
  typescriptEslint.configs.strictTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  // Config files are plain JavaScript, so they get no type information.
  {
    files: ["**/*.{js,mjs,cjs}"],
    extends: [typescriptEslint.configs.disableTypeChecked],
  },
  // Turns off ESLint rules that conflict with Prettier; keep after other rule sets.
  prettierCompatibility,
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);

export default eslintConfig;
