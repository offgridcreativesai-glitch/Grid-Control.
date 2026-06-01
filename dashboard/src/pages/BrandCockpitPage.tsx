/**
 * Brand Command Center — the primary cockpit (route "/").
 * Replaces the chat-first ClientDashboardPage as the operator's home for a single brand.
 * Composes the four real-data modules: Digest · Brain · Agents · Performance.
 */
import { useEffect } from "react"
import { useBrandStore } from "@/store/brandStore"
import { useAppStore } from "@/store/appStore"
import { CockpitRoot } from "@/components/cockpit/primitives"
import { CarouselComposer } from "@/components/cockpit/CarouselComposer"
import { DigestModule } from "@/components/cockpit/DigestModule"
import { BrainPanel } from "@/components/cockpit/BrainPanel"
import { AgentsModule } from "@/components/cockpit/AgentsModule"
import { PerformanceModule } from "@/components/cockpit/PerformanceModule"
import { ReadyToPublish } from "@/components/cockpit/ReadyToPublish"
import { OperatorToggle } from "@/components/cockpit/OperatorToggle"
import { brandMark } from "@/lib/cockpitFormat"

export function BrandCockpitPage() {
  const { activeBrand } = useBrandStore()
  const { setBrainOpen } = useAppStore()

  // The cockpit IS the Brain surface — close the right-rail Brain here.
  useEffect(() => {
    setBrainOpen(false)
  }, [setBrainOpen])

  return (
    <CockpitRoot>
      <div className="mx-auto max-w-[1240px] px-6 pb-20 pt-6">
        {/* Cockpit header: brand identity + operator toggle */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span
              className="grid h-7 w-7 place-items-center rounded-md text-[13px] font-semibold text-white"
              style={{
                background: "color-mix(in oklab, var(--accent) 32%, #15161a)",
                border: "1px solid color-mix(in oklab, var(--accent) 30%, transparent)",
              }}
            >
              {brandMark(activeBrand.name)}
            </span>
            <span className="text-[15px] font-semibold tracking-tight text-zinc-100">
              {activeBrand.name}
            </span>
            {activeBrand.handle && (
              <span className="font-mono text-[11px] text-zinc-600">{activeBrand.handle}</span>
            )}
          </div>
          <OperatorToggle />
        </div>

        {/* Create bar — generate your first carousel */}
        <CarouselComposer />

        {/* Top zone: Digest | Brain */}
        <section className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <DigestModule />
          <BrainPanel />
        </section>

        {/* Grid below: Agents | Performance */}
        <section className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
          <AgentsModule />
          <PerformanceModule />
        </section>

        {/* Approved carousels → publish to Instagram */}
        <ReadyToPublish />
      </div>
    </CockpitRoot>
  )
}
