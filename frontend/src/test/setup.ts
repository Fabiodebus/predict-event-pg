import "@testing-library/jest-dom/vitest";

// React 18 act() warning suppression in Vitest+jsdom — must be set before
// any component is rendered.
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
