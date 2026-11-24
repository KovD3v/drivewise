import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { DemoNotice, isSyntheticDemo } from "./DemoNotice";

test("only the public build variable set to true turns the demo notice on", () => {
  expect(isSyntheticDemo({ VITE_SYNTHETIC_DATA: "true" })).toBe(true);
  expect(isSyntheticDemo({ VITE_SYNTHETIC_DATA: "false" })).toBe(false);
  expect(isSyntheticDemo({})).toBe(false);
});

test("the notice says the catalogue is invented, and renders nothing otherwise", () => {
  const { container, rerender } = render(<DemoNotice show />);
  expect(screen.getByRole("note")).toHaveTextContent(/inventati/);
  rerender(<DemoNotice show={false} />);
  expect(container).toBeEmptyDOMElement();
});
