import { setNamespace } from "../lib/workspace";
import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";
afterEach(() => {
  cleanup();
  setNamespace("NORMAL");
  sessionStorage.clear();
  localStorage.clear();
  vi.restoreAllMocks();
});
HTMLDialogElement.prototype.showModal = function () {
  this.setAttribute("open", "");
};
HTMLDialogElement.prototype.close = function () {
  this.removeAttribute("open");
};

// Browser platform APIs used by Radix/cmdk; no application behavior is mocked.
class Observer {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = Observer;
HTMLElement.prototype.scrollIntoView = function () {};
