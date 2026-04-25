import { useState, useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { Check, Plus } from "lucide-react"
import { cn } from "@/lib/utils"
import { useBrandStore } from "@/store/brandStore"
import type { ApiResponse } from "@/types"
import { apiFetch } from "@/lib/api"

interface Brand {
  slug: string
  name: string
}

async function fetchBrands(): Promise<Brand[]> {
  const res = await apiFetch("/api/brands")
  const json: ApiResponse<Brand[]> = await res.json()
  if (!json.success) throw new Error(json.error)
  return json.data
}

export function BrandSwitcher() {
  const { activeBrand, setActiveBrand, setBrands, navigate } = useBrandStore()
  const [open, setOpen] = useState(false)

  const { data: brands = [], isSuccess } = useQuery({
    queryKey: ["brands"],
    queryFn: fetchBrands,
    refetchInterval: false,
    staleTime: 30000,
  })

  useEffect(() => {
    if (!isSuccess) return
    if (brands.length === 0) {
      navigate(4)
      return
    }
    setBrands(brands)
    const stillExists = brands.find(b => b.slug === activeBrand.slug)
    if (!stillExists) setActiveBrand(brands[0])
  }, [isSuccess, brands, setBrands, activeBrand.slug, setActiveBrand, navigate])

  const displayName = activeBrand.name || "Select Brand"

  return (
    <div className="relative mx-3 my-4">
      {/* Trigger — gold pill */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-[10px] rounded-[8px] transition-colors"
        style={{
          background: "rgba(201,168,76,0.12)",
          border: "1px solid rgba(201,168,76,0.2)",
        }}
      >
        {/* Active dot */}
        <span
          className="flex-shrink-0 rounded-full bg-[hsl(var(--gc-gold))]"
          style={{ width: 6, height: 6 }}
        />
        <span
          className="flex-1 text-left truncate text-[hsl(var(--gc-gold))]"
          style={{ fontSize: 13, fontWeight: 600 }}
        >
          {displayName}
        </span>
        {/* Caret */}
        <span
          className={cn(
            "text-[hsl(var(--gc-text-2))] transition-transform duration-150",
            open && "rotate-180"
          )}
          style={{ fontSize: 10 }}
        >
          ⌄
        </span>
      </button>

      {/* Dropdown */}
      {open && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
          />
          <div
            className="absolute left-0 right-0 top-full mt-1 z-50 rounded-[8px] overflow-hidden shadow-xl"
            style={{
              background: "hsl(var(--gc-surface))",
              border: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            {brands.map(brand => {
              const isSelected = brand.slug === activeBrand.slug
              return (
                <button
                  key={brand.slug}
                  onClick={() => { setActiveBrand(brand); setOpen(false) }}
                  className={cn(
                    "w-full flex items-center gap-2 px-3 py-2 text-left transition-colors",
                    "hover:bg-[hsl(var(--gc-surface2))]",
                    isSelected
                      ? "text-[hsl(var(--gc-gold))]"
                      : "text-[hsl(var(--foreground))]"
                  )}
                  style={{ fontSize: 13, fontWeight: isSelected ? 600 : 400 }}
                >
                  {isSelected
                    ? <Check size={10} className="flex-shrink-0" />
                    : <span className="w-[10px] flex-shrink-0" />
                  }
                  <span className="truncate">{brand.name}</span>
                </button>
              )
            })}

            <div
              className="border-t"
              style={{ borderColor: "rgba(255,255,255,0.06)" }}
            >
              <button
                onClick={() => { setOpen(false); navigate(4) }}
                className="w-full flex items-center gap-2 px-3 py-2 transition-colors hover:bg-[hsl(var(--gc-surface2))]"
                style={{ fontSize: 13 }}
              >
                <Plus size={12} className="text-[hsl(var(--gc-text-2))] flex-shrink-0" />
                <span className="text-[hsl(var(--gc-text-2))]">Add Brand</span>
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
