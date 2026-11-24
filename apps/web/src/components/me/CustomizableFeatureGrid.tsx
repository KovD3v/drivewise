import { useCallback, useEffect, useRef, useState } from "react";
import {
  AnimatePresence,
  motion,
  useDragControls,
  useReducedMotion,
  type PanInfo,
} from "framer-motion";
import {
  BrainCircuit,
  Check,
  EyeOff,
  Globe2,
  GripVertical,
  Warehouse,
  Wrench,
  Plus,
  Sparkles,
  SlidersHorizontal,
} from "lucide-react";
import { FeatureCard } from "./FeatureCard";
import { featureIcon } from "./icons";
import { FEATURES, SECTIONS, type Feature, type FeatureKey } from "@/lib/mydrivewise";
import { SmartGarageHero } from "./SmartGarageHero";
import { useDashboardLayout, defaultLayout } from "@/lib/dashboard-layout";
import { EASE } from "@/lib/motion";
import { cn } from "@/lib/utils";

const bySlug = (s: FeatureKey) => FEATURES.find((f) => f.slug === s)!;

const SECTION_ICON = {
  garage: Warehouse,
  wrench: Wrench,
  brain: BrainCircuit,
  globe: Globe2,
} as const;

export function CustomizableFeatureGrid() {
  const { layout, setLayout, hydrated } = useDashboardLayout();
  const [editing, setEditing] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const reduce = useReducedMotion();
  const nodes = useRef(new Map<FeatureKey, HTMLElement>());

  const visible = layout.order.filter((s) => !layout.hidden.includes(s));
  const hidden = layout.order.filter((s) => layout.hidden.includes(s));

  const move = useCallback(
    (from: FeatureKey, to: FeatureKey) => {
      if (from === to) return;
      const order = [...layout.order];
      const a = order.indexOf(from);
      const b = order.indexOf(to);
      if (a < 0 || b < 0) return;
      order.splice(a, 1);
      order.splice(b, 0, from);
      setLayout({ ...layout, order });
    },
    [layout, setLayout],
  );

  const hide = (slug: FeatureKey) =>
    setLayout({ ...layout, hidden: [...layout.hidden, slug] });

  const show = (slug: FeatureKey) => {
    const order = layout.order.filter((s) => s !== slug);
    const lastVisible = visible[visible.length - 1];
    const at = lastVisible ? order.indexOf(lastVisible) + 1 : 0;
    order.splice(at, 0, slug);
    setLayout({ order, hidden: layout.hidden.filter((s) => s !== slug) });
  };

  const findTarget = (slug: FeatureKey, x: number, y: number): FeatureKey | null => {
    let best: FeatureKey | null = null;
    let bestDist = Infinity;
    for (const s of visible) {
      if (s === slug) continue;
      const el = nodes.current.get(s);
      if (!el) continue;
      const r = el.getBoundingClientRect();
      if (x < r.left || x > r.right || y < r.top || y > r.bottom) continue;
      const d = Math.hypot(x - (r.left + r.width / 2), y - (r.top + r.height / 2));
      if (d < bestDist) {
        bestDist = d;
        best = s;
      }
    }
    return best;
  };

  return (
    <div>
      <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm text-muted-foreground">
          {editing
            ? "Trascina le card per riordinarle, nascondi quelle che non ti servono."
            : `${visible.length} funzionalità nella tua dashboard`}
        </div>
        <div className="flex items-center gap-2">
          <AnimatePresence initial={false}>
            {editing && (
              <motion.button
                key="add"
                type="button"
                initial={reduce ? false : { opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 8 }}
                transition={{ duration: 0.3, ease: EASE }}
                onClick={() => setDrawer((d) => !d)}
                className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/70 px-4 py-2 text-sm font-medium backdrop-blur transition-colors duration-300 hover:border-primary/45 hover:text-primary"
              >
                <Plus className="size-4" />
                Aggiungi funzionalità
                {hidden.length > 0 && (
                  <span className="rounded-full bg-primary/15 px-2 text-xs text-primary">
                    {hidden.length}
                  </span>
                )}
              </motion.button>
            )}
          </AnimatePresence>
          <button
            type="button"
            onClick={() => {
              setEditing((e) => !e);
              setDrawer(false);
            }}
            className={cn(
              "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium backdrop-blur transition-all duration-300",
              editing
                ? "border-primary/45 bg-primary/12 text-primary shadow-[var(--shadow-soft)]"
                : "border-border/70 bg-card/70 hover:border-primary/45 hover:text-primary",
            )}
          >
            {editing ? <Check className="size-4" /> : <SlidersHorizontal className="size-4" />}
            {editing ? "Fatto" : "Personalizza"}
          </button>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {editing && drawer && (
          <motion.div
            initial={reduce ? false : { opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.4, ease: EASE }}
            className="overflow-hidden"
          >
            <div className="mt-5 rounded-3xl border border-border/70 bg-card/70 p-5 backdrop-blur shadow-[var(--shadow-soft)]">
              <p className="font-heading text-sm font-extrabold tracking-tight">
                Aggiungi altre funzionalità
              </p>
              {hidden.length === 0 ? (
                <p className="mt-2 text-sm text-muted-foreground">
                  Hai già tutte le funzionalità in dashboard. Nascondine una per ritrovarla qui.
                </p>
              ) : (
                <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {hidden.map((slug) => {
                    const f = bySlug(slug);
                    const Icon = featureIcon(f.icon);
                    return (
                      <motion.button
                        key={slug}
                        type="button"
                        layout
                        onClick={() => show(slug)}
                        initial={reduce ? false : { opacity: 0, scale: 0.96 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.96 }}
                        transition={{ duration: 0.3, ease: EASE }}
                        className="group flex items-center gap-3 rounded-2xl border border-border/70 bg-background/60 p-3 text-left transition-all duration-300 hover:border-primary/40 hover:shadow-[var(--shadow-soft)]"
                      >
                        <span className="grid size-9 shrink-0 place-items-center rounded-full border border-primary/25 bg-primary/10 text-primary">
                          <Icon className="size-4" strokeWidth={1.8} />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium">{f.title}</span>
                          <span className="block truncate text-xs text-muted-foreground">
                            {f.short}
                          </span>
                        </span>
                        <span className="grid size-7 shrink-0 place-items-center rounded-full border border-border/70 text-muted-foreground transition-colors duration-300 group-hover:border-primary/45 group-hover:text-primary">
                          <Plus className="size-3.5" />
                        </span>
                      </motion.button>
                    );
                  })}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {hydrated && visible.length === 0 ? (
        <motion.div
          initial={reduce ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: EASE }}
          className="mt-6 rounded-3xl border border-dashed border-primary/35 bg-card/60 p-10 text-center backdrop-blur"
        >
          <span className="mx-auto grid size-12 place-items-center rounded-full border border-primary/25 bg-primary/10 text-primary">
            <Sparkles className="size-5" strokeWidth={1.8} />
          </span>
          <p className="mt-4 font-heading text-lg font-extrabold tracking-tight">
            La tua dashboard è tutta da comporre
          </p>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
            Aggiungi almeno una funzionalità per iniziare: puoi sempre cambiare idea più tardi.
          </p>
          <button
            type="button"
            onClick={() => {
              setEditing(true);
              setDrawer(true);
            }}
            className="mt-5 inline-flex items-center gap-2 rounded-full border border-primary/40 bg-primary/12 px-4 py-2 text-sm font-medium text-primary transition-colors duration-300 hover:bg-primary/18"
          >
            <Plus className="size-4" />
            Aggiungi una card
          </button>
          <button
            type="button"
            onClick={() => setLayout(defaultLayout())}
            className="ml-2 mt-5 inline-flex items-center gap-2 rounded-full border border-border/70 px-4 py-2 text-sm text-muted-foreground transition-colors duration-300 hover:text-foreground"
          >
            Ripristina tutte
          </button>
        </motion.div>
      ) : (
        <div className="mt-4">
          {SECTIONS.map((section, sIdx) => {
            const items = visible.filter((s) => section.items.includes(s));
            if (items.length === 0) return null;
            const heroSlug = items.find((s) => bySlug(s).hero);
            const rest = items.filter((s) => s !== heroSlug);
            const SectionIcon = SECTION_ICON[section.icon];
            return (
              <motion.section
                key={section.id}
                initial={reduce ? false : { opacity: 0, y: 26 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.6, ease: EASE }}
                className="relative mt-20 pt-12 first:mt-10 first:pt-0"
              >
                {sIdx > 0 && (
                  <span
                    aria-hidden
                    className="absolute left-7 right-0 top-0 h-px bg-[linear-gradient(to_right,color-mix(in_oklab,var(--color-primary)_50%,transparent),var(--color-border)_22%,transparent)]"
                  />
                )}
                <motion.div
                  initial={reduce ? false : { opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-80px" }}
                  transition={{ duration: 0.5, ease: EASE, delay: 0.08 }}
                  className="flex items-start gap-4"
                >
                  <motion.span
                    aria-hidden
                    initial={reduce ? false : { opacity: 0, scale: 0.6 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true, margin: "-80px" }}
                    transition={{ duration: 0.45, ease: EASE, type: "spring", bounce: 0.42 }}
                    className="relative grid size-14 shrink-0 place-items-center rounded-full border border-primary/30 bg-primary/10 text-primary shadow-[0_0_30px_-12px_var(--color-primary)] backdrop-blur"
                  >
                    <span
                      aria-hidden
                      className="pointer-events-none absolute inset-0 rounded-full bg-[radial-gradient(80%_80%_at_30%_20%,color-mix(in_oklab,var(--color-primary)_18%,transparent),transparent_70%)]"
                    />
                    <SectionIcon className="relative size-6" strokeWidth={1.8} />
                  </motion.span>
                  <span className="min-w-0">
                    <h3 className="font-heading text-xl font-extrabold tracking-tight sm:text-2xl">
                      {section.title}
                    </h3>
                    <p className="mt-2 max-w-2xl text-sm text-muted-foreground sm:text-base">
                      {section.subtitle}
                    </p>
                    </span>
                </motion.div>

                <div className="mt-7 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {heroSlug && !editing && <SmartGarageHero feature={bySlug(heroSlug)} />}
                  {(heroSlug && editing ? items : rest).map((slug, i) => (
                    <DraggableCard
                      key={slug}
                      feature={bySlug(slug)}
                      index={i}
                      editing={editing}
                      reduce={!!reduce}
                      register={(el) => {
                        if (el) nodes.current.set(slug, el);
                        else nodes.current.delete(slug);
                      }}
                      onHide={() => hide(slug)}
                      onDragMove={(x, y) => {
                        const t = findTarget(slug, x, y);
                        if (t) move(slug, t);
                      }}
                    />
                  ))}
                </div>
              </motion.section>
            );
          })}
        </div>
      )}
    </div>
  );
}

function DraggableCard({
  feature,
  index,
  editing,
  reduce,
  register,
  onHide,
  onDragMove,
}: {
  feature: Feature;
  index: number;
  editing: boolean;
  reduce: boolean;
  register: (el: HTMLElement | null) => void;
  onHide: () => void;
  onDragMove: (x: number, y: number) => void;
}) {
  const controls = useDragControls();
  const [dragging, setDragging] = useState(false);
  const holdRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastMove = useRef(0);

  useEffect(
    () => () => {
      if (holdRef.current) clearTimeout(holdRef.current);
    },
    [],
  );

  const startHold = (e: React.PointerEvent) => {
    if (!editing) return;
    const ev = e;
    holdRef.current = setTimeout(() => controls.start(ev), 260);
  };
  const cancelHold = () => {
    if (holdRef.current) clearTimeout(holdRef.current);
    holdRef.current = null;
  };

  const handleDrag = (e: PointerEvent | MouseEvent | TouchEvent, _info: PanInfo) => {
    const now = performance.now();
    if (now - lastMove.current < 90) return;
    lastMove.current = now;
    const p = e as PointerEvent;
    if (typeof p.clientX === "number") onDragMove(p.clientX, p.clientY);
  };

  return (
    <motion.div
      ref={register}
      layout={!reduce}
      transition={{ layout: { duration: 0.4, ease: EASE }, duration: 0.3, ease: EASE }}
      drag={editing}
      dragListener={false}
      dragControls={controls}
      dragSnapToOrigin
      dragElastic={0.14}
      dragMomentum={false}
      onDragStart={() => setDragging(true)}
      onDrag={handleDrag}
      onDragEnd={() => setDragging(false)}
      onPointerDown={startHold}
      onPointerUp={cancelHold}
      onPointerCancel={cancelHold}
      style={{ touchAction: editing ? "none" : undefined }}
      animate={
        dragging
          ? { scale: 1.03, rotate: -1.2, zIndex: 40 }
          : editing && !reduce
            ? { rotate: [0, -0.45, 0, 0.45, 0], scale: 1, zIndex: 0 }
            : { rotate: 0, scale: 1, zIndex: 0 }
      }
      className={cn(
        "relative",
        feature.hero && "sm:col-span-2 sm:row-span-2",
        dragging && "cursor-grabbing drop-shadow-[0_28px_50px_rgba(17,24,39,0.22)]",
      )}
    >
      <motion.div
        animate={
          editing && !dragging && !reduce ? { rotate: [0, -0.5, 0, 0.5, 0] } : { rotate: 0 }
        }
        transition={
          editing && !dragging && !reduce
            ? { duration: 2.4, repeat: Infinity, ease: "easeInOut", delay: (index % 5) * 0.12 }
            : { duration: 0.3, ease: EASE }
        }
        className={cn("h-full", editing && "select-none")}
      >
        <div className={cn("h-full", editing && "pointer-events-none")}>
          <FeatureCard feature={feature} index={index} inGrid />
        </div>
      </motion.div>

      <AnimatePresence>
        {editing && (
          <>
            <motion.button
              type="button"
              aria-label={`Sposta ${feature.title}`}
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.85 }}
              transition={{ duration: 0.25, ease: EASE }}
              onPointerDown={(e) => {
                e.stopPropagation();
                cancelHold();
                controls.start(e);
              }}
              className="absolute left-3 top-3 z-20 grid size-8 cursor-grab place-items-center rounded-full border border-border/70 bg-background/85 text-muted-foreground backdrop-blur transition-colors duration-300 hover:border-primary/45 hover:text-primary active:cursor-grabbing"
            >
              <GripVertical className="size-4" />
            </motion.button>
            <motion.button
              type="button"
              aria-label={`Nascondi ${feature.title}`}
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.85 }}
              transition={{ duration: 0.25, ease: EASE, delay: 0.04 }}
              onPointerDown={(e) => e.stopPropagation()}
              onClick={onHide}
              className="absolute left-14 top-3 z-20 grid size-8 place-items-center rounded-full border border-border/70 bg-background/85 text-muted-foreground backdrop-blur transition-colors duration-300 hover:border-primary/45 hover:text-primary"
            >
              <EyeOff className="size-4" />
            </motion.button>
          </>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
