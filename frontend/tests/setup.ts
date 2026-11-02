import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

Object.defineProperty(window, "matchMedia", { writable: true, value: vi.fn().mockImplementation((query) => ({
  matches: false, media: query, onchange: null, addListener: vi.fn(), removeListener: vi.fn(),
  addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn(),
})) });
class Observer { observe() {} unobserve() {} disconnect() {} }
vi.stubGlobal("ResizeObserver", Observer);
vi.stubGlobal("IntersectionObserver", Observer);
HTMLElement.prototype.scrollIntoView = vi.fn();
window.scrollTo = vi.fn();
const computed = window.getComputedStyle;
window.getComputedStyle = (el) => computed(el);
const context = {
  setTransform: vi.fn(), clearRect: vi.fn(), drawImage: vi.fn(), beginPath: vi.fn(), moveTo: vi.fn(),
  lineTo: vi.fn(), arcTo: vi.fn(), closePath: vi.fn(), fill: vi.fn(), stroke: vi.fn(), fillRect: vi.fn(),
  clip: vi.fn(), save: vi.fn(), restore: vi.fn(), translate: vi.fn(), rotate: vi.fn(), scale: vi.fn(), arc: vi.fn(),
  createLinearGradient: () => ({ addColorStop: vi.fn() }),
};
HTMLCanvasElement.prototype.getContext = vi.fn(() => context) as never;
HTMLCanvasElement.prototype.toDataURL = vi.fn(() => "data:image/png;base64,");
afterEach(() => { cleanup(); localStorage.clear(); vi.restoreAllMocks(); vi.useRealTimers(); });
