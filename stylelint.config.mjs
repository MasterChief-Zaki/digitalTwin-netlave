/** @type {import("stylelint").Config} */
const stylelintConfig = {
  extends: ["stylelint-config-standard-scss"],
  rules: {
    // CSS Modules classes are read in TSX as `styles.className`, so use camelCase.
    "selector-class-pattern": [
      "^[a-z][a-zA-Z0-9]*$",
      { message: "Expected class selector to be camelCase" },
    ],
  },
};

export default stylelintConfig;
