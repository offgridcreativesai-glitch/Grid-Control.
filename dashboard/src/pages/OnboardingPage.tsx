import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { apiFetch } from "@/lib/api"
import { useBrandStore } from "@/store/brandStore"

type Step = 1 | 2 | 3

interface BrandData {
  name: string
  slug: string
  product: string
  audience: string
  website: string
  instagram: string
  linkedin: string
  youtube: string
  tiktok: string
}

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 60)
}

export function OnboardingPage() {
  const navigate = useNavigate()
  const { setActiveBrand, setBrands, brands } = useBrandStore()
  const [step, setStep] = useState<Step>(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [data, setData] = useState<BrandData>({
    name: "", slug: "", product: "", audience: "",
    website: "", instagram: "", linkedin: "", youtube: "", tiktok: "",
  })

  function update(field: keyof BrandData, value: string) {
    setData((prev) => {
      const next = { ...prev, [field]: value }
      if (field === "name" && !prev.slug) {
        next.slug = slugify(value)
      }
      return next
    })
  }

  async function handleCreate() {
    setLoading(true)
    setError("")
    const slug = data.slug || slugify(data.name)
    const profile = {
      name: data.name,
      product_description: data.product,
      target_audience: data.audience,
      website: data.website,
      social_handles: {
        instagram: data.instagram,
        linkedin: data.linkedin,
        youtube: data.youtube,
        tiktok: data.tiktok,
      },
      platforms: [
        data.instagram && "Instagram",
        data.linkedin && "LinkedIn",
        data.youtube && "YouTube",
        data.tiktok && "TikTok",
      ].filter(Boolean),
    }

    try {
      const res = await apiFetch("/api/auth/create-brand", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug, name: data.name, profile }),
      })
      const json = await res.json()
      if (!json.success) {
        setError(json.error || "Failed to create brand")
        setLoading(false)
        return
      }

      const newBrand = { slug, name: data.name, primary: brands.length === 0 }
      setBrands([...brands, newBrand])
      setActiveBrand(newBrand)
      navigate("/")
    } catch (e) {
      setError("Network error")
    }
    setLoading(false)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <div className="flex items-center gap-3 mb-1">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`h-1 flex-1 rounded-full ${s <= step ? "bg-primary" : "bg-muted"}`}
              />
            ))}
          </div>
          <CardTitle className="text-lg">
            {step === 1 && "Tell us about your brand"}
            {step === 2 && "Connect your platforms"}
            {step === 3 && "Review and launch"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {step === 1 && (
            <>
              <div className="space-y-1">
                <label className="text-sm font-medium text-muted-foreground">Brand name</label>
                <Input
                  placeholder="e.g. DropVolt"
                  value={data.name}
                  onChange={(e) => update("name", e.target.value)}
                  autoFocus
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-muted-foreground">What do you sell?</label>
                <Input
                  placeholder="e.g. Graphic tees for Gen Z streetwear enthusiasts"
                  value={data.product}
                  onChange={(e) => update("product", e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-muted-foreground">Who is your audience?</label>
                <Input
                  placeholder="e.g. 18-28 year old men into streetwear, sneakers, anime"
                  value={data.audience}
                  onChange={(e) => update("audience", e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium text-muted-foreground">Website URL (optional)</label>
                <Input
                  placeholder="https://dropvolt.com"
                  value={data.website}
                  onChange={(e) => update("website", e.target.value)}
                />
              </div>
              <Button
                className="w-full"
                disabled={!data.name.trim() || !data.product.trim()}
                onClick={() => setStep(2)}
              >
                Next
              </Button>
            </>
          )}

          {step === 2 && (
            <>
              <p className="text-sm text-muted-foreground">
                Add your social handles so agents can analyze your content and competitors.
              </p>
              <div className="space-y-3">
                <Input
                  placeholder="Instagram handle (e.g. @dropvolt)"
                  value={data.instagram}
                  onChange={(e) => update("instagram", e.target.value)}
                />
                <Input
                  placeholder="LinkedIn page URL or handle"
                  value={data.linkedin}
                  onChange={(e) => update("linkedin", e.target.value)}
                />
                <Input
                  placeholder="YouTube channel URL"
                  value={data.youtube}
                  onChange={(e) => update("youtube", e.target.value)}
                />
                <Input
                  placeholder="TikTok handle (e.g. @dropvolt)"
                  value={data.tiktok}
                  onChange={(e) => update("tiktok", e.target.value)}
                />
              </div>
              <div className="flex gap-2">
                <Button variant="outline" className="flex-1" onClick={() => setStep(1)}>
                  Back
                </Button>
                <Button className="flex-1" onClick={() => setStep(3)}>
                  Next
                </Button>
              </div>
            </>
          )}

          {step === 3 && (
            <>
              <div className="rounded-lg border border-border bg-card p-4 space-y-2 text-sm">
                <div><span className="text-muted-foreground">Brand:</span> {data.name}</div>
                <div><span className="text-muted-foreground">Product:</span> {data.product}</div>
                <div><span className="text-muted-foreground">Audience:</span> {data.audience || "—"}</div>
                {data.website && <div><span className="text-muted-foreground">Website:</span> {data.website}</div>}
                {data.instagram && <div><span className="text-muted-foreground">Instagram:</span> {data.instagram}</div>}
                {data.linkedin && <div><span className="text-muted-foreground">LinkedIn:</span> {data.linkedin}</div>}
                {data.youtube && <div><span className="text-muted-foreground">YouTube:</span> {data.youtube}</div>}
                {data.tiktok && <div><span className="text-muted-foreground">TikTok:</span> {data.tiktok}</div>}
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <div className="flex gap-2">
                <Button variant="outline" className="flex-1" onClick={() => setStep(2)}>
                  Back
                </Button>
                <Button className="flex-1" disabled={loading} onClick={handleCreate}>
                  {loading ? "Creating..." : "Launch brand"}
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
