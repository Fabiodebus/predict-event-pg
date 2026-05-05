import "@testing-library/jest-dom/vitest";

declare global {
  // React testing utility flag — enables proper act() warning behavior.
  // eslint-disable-next-line no-var
  var IS_REACT_ACT_ENVIRONMENT: boolean;
}

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
