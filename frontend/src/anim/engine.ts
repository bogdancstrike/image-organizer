/**
 * SortEngine: the pile → fly → card animation (spec REQ-UI-2), drawn on one canvas.
 *
 * - Every file becomes a sprite with a pre-rendered "polaroid" tile (white border + shadow baked in),
 *   so a frame is just one drawImage per sprite.
 * - Pile positions are stored in polar, normalized units and re-projected every frame, so the pile
 *   follows layout changes. Landed sprites re-read their card's slot area rect every frame.
 * - Flights are released at an adaptive rate so a run lasts about 5 s whatever the file count.
 */

const PILE = 42; // px, sprite size in the pile
const SLOT = 20; // px, sprite size inside a card
const GAP = 3;
const PAD = 8; // tile padding around the photo (room for the shadow)
const FLIGHT_MS = 760;
const APPEAR_MS = 380;
const TARGET_SECONDS = 5;

type State = "pile" | "flying" | "landed" | "gone";

interface Sprite {
  id: string;
  tile: HTMLCanvasElement | null;
  pu: number; // 0..1 radial (sqrt-distributed)
  pa: number; // angle
  prot: number;
  born: number;
  wobble: number;
  state: State;
  key?: string;
  slot?: number;
  overflow?: boolean;
  fx?: number;
  fy?: number;
  frot?: number;
  t0?: number;
  arc?: number;
  alpha: number;
}

export interface EngineHooks {
  stage: () => HTMLElement | null;
  pile: () => HTMLElement | null;
  slotArea: (key: string) => HTMLElement | null;
  onLand: (key: string, id: string) => void;
}

const easeInOutCubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeOutBack = (t: number) => 1 + 2.2 * Math.pow(t - 1, 3) + 1.2 * Math.pow(t - 1, 2);

function roundRect(g: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  g.beginPath();
  g.moveTo(x + r, y);
  g.arcTo(x + w, y, x + w, y + h, r);
  g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r);
  g.arcTo(x, y, x + w, y, r);
  g.closePath();
}

function makeTile(img: HTMLImageElement | null, dpr: number): HTMLCanvasElement {
  const full = PILE + PAD * 2;
  const c = document.createElement("canvas");
  c.width = c.height = Math.ceil(full * dpr);
  const g = c.getContext("2d")!;
  g.scale(dpr, dpr);
  g.shadowColor = "rgba(90,30,70,.30)";
  g.shadowBlur = 9;
  g.shadowOffsetY = 3;
  roundRect(g, PAD, PAD, PILE, PILE, 8);
  g.fillStyle = "#fff";
  g.fill();
  g.shadowColor = "transparent";
  g.save();
  roundRect(g, PAD + 2.5, PAD + 2.5, PILE - 5, PILE - 5, 6);
  g.clip();
  if (img && img.naturalWidth) {
    const inner = PILE - 5;
    const s = Math.max(inner / img.naturalWidth, inner / img.naturalHeight);
    const w = img.naturalWidth * s;
    const h = img.naturalHeight * s;
    g.drawImage(img, PAD + 2.5 + (inner - w) / 2, PAD + 2.5 + (inner - h) / 2, w, h);
  } else {
    const grad = g.createLinearGradient(0, PAD, 0, PAD + PILE);
    grad.addColorStop(0, "#fde3ee");
    grad.addColorStop(1, "#f4b9d1");
    g.fillStyle = grad;
    g.fillRect(PAD, PAD, PILE, PILE);
  }
  g.restore();
  return c;
}

export class SortEngine {
  private ctx: CanvasRenderingContext2D;
  private dpr = Math.min(window.devicePixelRatio || 1, 2);
  private sprites = new Map<string, Sprite>();
  private order: Sprite[] = [];
  private queue: { id: string; key: string }[] = [];
  private slots = new Map<string, number>();
  private placeholder: HTMLCanvasElement;
  private expected = 0;
  private perFrame = 1;
  private acc = 0;
  private wobbling = false;
  private raf = 0;
  private ro: ResizeObserver;
  private rectCache = new Map<string, DOMRect | null>();
  private w = 0;
  private h = 0;
  reduced = false;

  constructor(
    private canvas: HTMLCanvasElement,
    private hooks: EngineHooks,
  ) {
    this.ctx = canvas.getContext("2d")!;
    this.placeholder = makeTile(null, this.dpr);
    this.ro = new ResizeObserver(() => this.resize());
    const stage = hooks.stage();
    if (stage) this.ro.observe(stage);
    this.resize();
    this.raf = requestAnimationFrame(this.frame);
  }

  destroy() {
    cancelAnimationFrame(this.raf);
    this.ro.disconnect();
  }

  reset() {
    this.sprites.clear();
    this.order = [];
    this.queue = [];
    this.slots.clear();
    this.expected = 0;
    this.acc = 0;
  }

  setExpected(total: number) {
    this.expected = total;
  }

  setWobble(on: boolean) {
    this.wobbling = on;
  }

  /** Total number of assignments that will arrive; sets the release rate. */
  expectAssigns(n: number) {
    this.perFrame = this.reduced ? n : Math.max(1, n / (60 * TARGET_SECONDS));
  }

  get pendingFlights() {
    return this.queue.length + this.order.filter((s) => s.state === "flying").length;
  }

  addFile(id: string, url: string) {
    if (this.sprites.has(id)) return;
    const s: Sprite = {
      id,
      tile: null,
      pu: Math.sqrt(Math.random()),
      pa: Math.random() * Math.PI * 2,
      prot: ((Math.random() - 0.5) * 50 * Math.PI) / 180,
      born: performance.now(),
      wobble: Math.random() * 10,
      state: "pile",
      alpha: 1,
    };
    this.sprites.set(id, s);
    this.order.push(s);
    const img = new Image();
    img.decoding = "async";
    img.onload = () => {
      s.tile = makeTile(img, this.dpr);
    };
    img.src = url;
  }

  assign(id: string, key: string) {
    this.queue.push({ id, key });
  }

  private resize() {
    const stage = this.hooks.stage();
    if (!stage) return;
    const r = stage.getBoundingClientRect();
    this.w = r.width;
    this.h = r.height;
    this.canvas.width = Math.round(r.width * this.dpr);
    this.canvas.height = Math.round(r.height * this.dpr);
    this.canvas.style.width = `${r.width}px`;
    this.canvas.style.height = `${r.height}px`;
  }

  private rect(key: string): DOMRect | null {
    if (!this.rectCache.has(key)) {
      const el = this.hooks.slotArea(key);
      this.rectCache.set(key, el ? el.getBoundingClientRect() : null);
    }
    return this.rectCache.get(key)!;
  }

  private slotPos(key: string, slot: number, stage: DOMRect) {
    const r = this.rect(key);
    if (!r) return null;
    const cols = Math.max(1, Math.floor((r.width + GAP) / (SLOT + GAP)));
    const rows = Math.max(1, Math.floor((r.height + GAP) / (SLOT + GAP)));
    const cap = cols * rows;
    const s = Math.min(slot, cap - 1);
    return {
      x: r.left - stage.left + (s % cols) * (SLOT + GAP) + SLOT / 2,
      y: r.top - stage.top + Math.floor(s / cols) * (SLOT + GAP) + SLOT / 2,
      overflow: slot >= cap,
    };
  }

  private pileGeom(stage: DOMRect) {
    const p = this.hooks.pile();
    if (!p) return { cx: this.w / 2, cy: this.h / 2, R: 100 };
    const r = p.getBoundingClientRect();
    const maxR = Math.max(40, Math.min(r.width, r.height) / 2 - PILE * 0.7);
    const R = Math.min(maxR, 15 * Math.sqrt(Math.max(this.expected, this.order.length)) + 24);
    return { cx: r.left - stage.left + r.width / 2, cy: r.top - stage.top + r.height / 2, R };
  }

  private launch(now: number, pile: { cx: number; cy: number; R: number }) {
    this.acc += this.perFrame;
    while (this.acc >= 1 && this.queue.length) {
      const next = this.queue[0];
      if (!this.rect(next.key)) break; // card not rendered yet; retry next frame
      this.queue.shift();
      this.acc -= 1;
      const s = this.sprites.get(next.id);
      if (!s) continue;
      const slot = this.slots.get(next.key) ?? 0;
      this.slots.set(next.key, slot + 1);
      s.key = next.key;
      s.slot = slot;
      s.fx = pile.cx + Math.cos(s.pa) * s.pu * pile.R;
      s.fy = pile.cy + Math.sin(s.pa) * s.pu * pile.R;
      s.frot = s.prot;
      s.t0 = now;
      s.arc = (40 + Math.random() * 70) * (Math.random() < 0.5 ? -1 : 1);
      s.state = "flying";
      if (this.reduced) this.land(s);
    }
    if (!this.queue.length) this.acc = 0;
  }

  private land(s: Sprite) {
    s.state = "landed";
    this.hooks.onLand(s.key!, s.id);
  }

  private draw(s: Sprite, x: number, y: number, size: number, rot: number, alpha: number) {
    const tile = s.tile ?? this.placeholder;
    const full = (size * (PILE + PAD * 2)) / PILE;
    const d = this.dpr;
    const c = Math.cos(rot) * d;
    const n = Math.sin(rot) * d;
    this.ctx.globalAlpha = alpha;
    this.ctx.setTransform(c, n, -n, c, x * d, y * d);
    this.ctx.drawImage(tile, -full / 2, -full / 2, full, full);
  }

  private frame = (now: number) => {
    this.raf = requestAnimationFrame(this.frame);
    const stageEl = this.hooks.stage();
    if (!stageEl) return;
    const stage = stageEl.getBoundingClientRect();
    if (Math.abs(stage.width - this.w) > 0.5 || Math.abs(stage.height - this.h) > 0.5) this.resize();
    this.rectCache.clear();
    const ctx = this.ctx;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    if (!this.order.length) return;

    const pile = this.pileGeom(stage);
    if (this.queue.length) this.launch(now, pile);

    const flying: Sprite[] = [];
    // 1) pile + landed
    for (const s of this.order) {
      if (s.state === "pile") {
        const age = Math.min(1, (now - s.born) / APPEAR_MS);
        const k = this.reduced ? 1 : easeOutBack(age);
        const wob = this.wobbling && !this.reduced ? Math.sin(now / 520 + s.wobble) * 0.05 : 0;
        const x = pile.cx + Math.cos(s.pa) * s.pu * pile.R;
        const y = pile.cy + Math.sin(s.pa) * s.pu * pile.R - (1 - age) * 18;
        this.draw(s, x, y, PILE * (0.6 + 0.4 * k), s.prot + wob, age);
      } else if (s.state === "landed") {
        const p = this.slotPos(s.key!, s.slot!, stage);
        if (!p) continue;
        if (p.overflow) {
          s.alpha -= 0.06;
          if (s.alpha <= 0) {
            s.state = "gone";
            continue;
          }
        }
        this.draw(s, p.x, p.y, SLOT, 0, s.alpha);
      } else if (s.state === "flying") {
        flying.push(s);
      }
    }
    // 2) flights on top
    for (const s of flying) {
      const p = this.slotPos(s.key!, s.slot!, stage);
      if (!p) continue;
      const t = Math.min(1, (now - s.t0!) / FLIGHT_MS);
      const e = easeInOutCubic(t);
      const dx = p.x - s.fx!;
      const dy = p.y - s.fy!;
      const len = Math.hypot(dx, dy) || 1;
      const lift = Math.sin(Math.PI * e) * s.arc!;
      const x = s.fx! + dx * e + (-dy / len) * lift;
      const y = s.fy! + dy * e + (dx / len) * lift;
      const size = PILE + (SLOT - PILE) * e;
      const pop = 1 + Math.sin(Math.PI * Math.min(1, t * 1.4)) * 0.18; // lift-off bump
      this.draw(s, x, y, size * pop, s.frot! * (1 - e), 1);
      if (t >= 1) this.land(s);
    }
    ctx.globalAlpha = 1;
  };
}
