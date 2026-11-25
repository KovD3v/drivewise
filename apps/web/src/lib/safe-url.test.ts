import { expect, test } from "vitest";
import { safeHttpsUrl } from "./safe-url";

test("keeps absolute https links and rejects every other scheme or shape", () => {
  expect(safeHttpsUrl("https://example.test/listino")).toBe("https://example.test/listino");
  expect(safeHttpsUrl("http://example.test/listino")).toBeNull();
  expect(safeHttpsUrl("javascript:alert(1)")).toBeNull();
  expect(safeHttpsUrl("JaVaScRiPt:alert(1)")).toBeNull();
  expect(safeHttpsUrl("data:text/html,<script>alert(1)</script>")).toBeNull();
  expect(safeHttpsUrl("/relative/path")).toBeNull();
  expect(safeHttpsUrl("")).toBeNull();
  expect(safeHttpsUrl(null)).toBeNull();
  expect(safeHttpsUrl(undefined)).toBeNull();
});
