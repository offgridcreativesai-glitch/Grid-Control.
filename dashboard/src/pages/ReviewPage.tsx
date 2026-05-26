import { useState, useEffect, useCallback, useMemo } from "react";
import { Check, X, Edit3, Send, ChevronDown, ChevronUp } from "lucide-react";
import { cn, formatTime } from "@/lib/utils";
import { type PendingApproval } from "@/data/mock";
import { type Platform } from "@/store/appStore";
import { StatusDot } from "@/components/ui/status-dot";
import { PlatformIcon } from "@/components/ui/platform-icon";
import { Button } from "@/components/ui/button";
import { usePendingOutputs, useApproveOutput, useRejectOutput, type PendingOutput } from "@/hooks/useGridApi";

function inferPlatform(po: PendingOutput): Platform {
  const hay = `${po.platform ?? ""} ${po.filename} ${po.agent_slug}`.toLowerCase();
  if (hay.includes("instagram") || hay.includes("ig")) return "instagram";
  if (hay.includes("linkedin") || hay.includes("li")) return "linkedin";
  if (hay.includes("tiktok") || hay.includes("tt")) return "tiktok";
  if (hay.includes("youtube") || hay.includes("yt")) return "youtube";
  return "x";
}

function adaptOutput(po: PendingOutput): PendingApproval {
  // Caption — prefer the structured caption; fall back to body_text or preview.
  const caption = po.caption || po.body_text || po.preview || "(no caption)";
  return {
    id: po.filename,
    platform: inferPlatform(po),
    draftedBy: po.agent_name || po.agent_slug,
    scheduledTime: po.scheduled_for ? new Date(po.scheduled_for) : new Date(po.created_at),
    title: po.title || undefined,
    caption,
    hashtags: po.hashtags || [],
    script: po.body_text || undefined,
    slideImages: po.slide_images || [],
    status: "pending",
  };
}

export function ReviewPage() {
  const { data } = usePendingOutputs();
  const approveMut = useApproveOutput();
  const rejectMut = useRejectOutput();

  const approvals: PendingApproval[] = useMemo(
    () => (data?.outputs ?? []).map(adaptOutput),
    [data],
  );

  const [selectedId, setSelectedId] = useState<string | null>(null);
  useEffect(() => {
    if (!selectedId && approvals.length > 0) setSelectedId(approvals[0].id);
  }, [approvals, selectedId]);
  const [showScript, setShowScript] = useState(false);

  const selected = approvals.find((a) => a.id === selectedId);
  const pendingApprovals = approvals.filter((a) => a.status === "pending");

  const navigateToNext = useCallback(() => {
    const currentIndex = pendingApprovals.findIndex((a) => a.id === selectedId);
    if (currentIndex < pendingApprovals.length - 1) {
      setSelectedId(pendingApprovals[currentIndex + 1].id);
    }
  }, [pendingApprovals, selectedId]);

  const navigateToPrev = useCallback(() => {
    const currentIndex = pendingApprovals.findIndex((a) => a.id === selectedId);
    if (currentIndex > 0) {
      setSelectedId(pendingApprovals[currentIndex - 1].id);
    }
  }, [pendingApprovals, selectedId]);

  const handleApprove = useCallback(() => {
    if (!selectedId) return;
    approveMut.mutate(selectedId);
    navigateToNext();
  }, [selectedId, navigateToNext, approveMut]);

  const handleReject = useCallback(() => {
    if (!selectedId) return;
    rejectMut.mutate(selectedId);
    navigateToNext();
  }, [selectedId, navigateToNext, rejectMut]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      switch (e.key.toLowerCase()) {
        case "a":
          handleApprove();
          break;
        case "r":
          handleReject();
          break;
        case "j":
          if (!e.metaKey && !e.ctrlKey) navigateToNext();
          break;
        case "k":
          navigateToPrev();
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleApprove, handleReject, navigateToNext, navigateToPrev]);

  if (pendingApprovals.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-medium">No drafts waiting.</p>
          <p className="text-sm text-muted-foreground mt-1">
            The agents are quiet. Enjoy it.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Left: Approval List */}
      <div className="w-80 border-r border-border overflow-auto">
        <div className="p-4 border-b border-border">
          <h2 className="text-sm font-medium">
            Pending approvals{" "}
            <span className="text-muted-foreground">({pendingApprovals.length})</span>
          </h2>
        </div>
        <div className="divide-y divide-border">
          {approvals.map((approval) => (
            <button
              key={approval.id}
              onClick={() => setSelectedId(approval.id)}
              className={cn(
                "w-full px-4 py-3 text-left hover:bg-secondary/50 transition-colors",
                selectedId === approval.id && "bg-secondary",
                approval.status !== "pending" && "opacity-50"
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                <PlatformIcon platform={approval.platform} className="h-3.5 w-3.5" />
                <span className="text-xs text-muted-foreground">
                  {approval.draftedBy}
                </span>
                <StatusDot
                  status={
                    approval.status === "approved"
                      ? "success"
                      : approval.status === "rejected"
                      ? "error"
                      : "queued"
                  }
                  className="ml-auto"
                />
              </div>
              {approval.title && (
                <p className="text-sm font-medium line-clamp-1 mb-0.5">{approval.title}</p>
              )}
              <p className="text-xs text-muted-foreground line-clamp-2">{approval.caption}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Right: Draft Preview */}
      {selected && (
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center gap-4 border-b border-border px-6 py-4">
            <div className="flex items-center gap-2">
              <PlatformIcon platform={selected.platform} className="h-5 w-5" />
              <span className="text-sm font-medium capitalize">
                {selected.platform}
              </span>
            </div>
            <span className="text-xs text-muted-foreground">
              Drafted by {selected.draftedBy}
            </span>
            <span className="text-xs font-mono text-muted-foreground ml-auto">
              Scheduled: {formatTime(selected.scheduledTime)}
            </span>
          </div>

          {/* Preview */}
          <div className="flex-1 overflow-auto p-6">
            <div className="max-w-lg mx-auto">
              {/* Platform-specific preview card */}
              <PostPreview approval={selected} />

              {/* Caption */}
              <div className="mt-6 space-y-4">
                <div>
                  <h3 className="text-xs font-medium text-muted-foreground mb-2">
                    Caption
                  </h3>
                  <p className="text-sm whitespace-pre-wrap">{selected.caption}</p>
                </div>

                {selected.hashtags.length > 0 && (
                  <div>
                    <h3 className="text-xs font-medium text-muted-foreground mb-2">
                      Hashtags
                    </h3>
                    <div className="flex flex-wrap gap-1">
                      {selected.hashtags.map((tag) => (
                        <span
                          key={tag}
                          className="text-xs text-primary"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {selected.script && (
                  <div>
                    <button
                      onClick={() => setShowScript(!showScript)}
                      className="flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {showScript ? (
                        <ChevronUp className="h-3 w-3" />
                      ) : (
                        <ChevronDown className="h-3 w-3" />
                      )}
                      Script
                    </button>
                    {showScript && (
                      <pre className="mt-2 text-xs font-mono text-muted-foreground whitespace-pre-wrap bg-secondary/50 rounded p-3">
                        {selected.script}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Action Bar */}
          <div className="flex items-center justify-between border-t border-border px-6 py-4">
            <div className="text-xs text-muted-foreground font-mono space-x-4">
              <span><kbd className="px-1.5 py-0.5 rounded bg-secondary">A</kbd> approve</span>
              <span><kbd className="px-1.5 py-0.5 rounded bg-secondary">R</kbd> reject</span>
              <span><kbd className="px-1.5 py-0.5 rounded bg-secondary">E</kbd> edit</span>
              <span><kbd className="px-1.5 py-0.5 rounded bg-secondary">J</kbd>/<kbd className="px-1.5 py-0.5 rounded bg-secondary">K</kbd> navigate</span>
              <span><kbd className="px-1.5 py-0.5 rounded bg-secondary">⌘↵</kbd> approve & schedule</span>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={handleReject}>
                <X className="h-4 w-4 mr-1" />
                Reject
              </Button>
              <Button variant="outline" size="sm">
                <Edit3 className="h-4 w-4 mr-1" />
                Edit
              </Button>
              <Button variant="outline" size="sm" onClick={handleApprove}>
                <Check className="h-4 w-4 mr-1" />
                Approve
              </Button>
              <Button size="sm" onClick={handleApprove}>
                <Send className="h-4 w-4 mr-1" />
                Approve & Schedule
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function PostPreview({ approval }: { approval: PendingApproval }) {
  const baseClasses = "rounded-lg border border-border bg-card overflow-hidden";
  const slides = approval.slideImages ?? [];
  const mediaUrl = (path: string) => `/api/outputs/media/${path}`;

  switch (approval.platform) {
    case "instagram":
      return (
        <div className={baseClasses}>
          {slides.length > 0 ? (
            <div className="aspect-square bg-secondary overflow-hidden relative">
              <div className="flex h-full snap-x snap-mandatory overflow-x-auto">
                {slides.map((path, i) => (
                  <img
                    key={path}
                    src={mediaUrl(path)}
                    alt={`Slide ${i + 1}`}
                    className="h-full w-full flex-shrink-0 object-contain snap-center"
                    onError={(e) => {
                      (e.currentTarget as HTMLImageElement).style.display = "none";
                    }}
                  />
                ))}
              </div>
              {slides.length > 1 && (
                <div className="absolute top-2 right-2 rounded-full bg-black/60 px-2 py-0.5 text-[10px] font-mono text-white">
                  1 / {slides.length}
                </div>
              )}
            </div>
          ) : (
            <div className="aspect-square bg-secondary flex items-center justify-center">
              <span className="text-muted-foreground text-sm">No image yet</span>
            </div>
          )}
          <div className="p-3">
            <div className="flex items-center gap-2 mb-2">
              <div className="h-8 w-8 rounded-full bg-secondary" />
              <span className="text-sm font-medium">askgauravai</span>
            </div>
            <p className="text-sm line-clamp-3 whitespace-pre-wrap">{approval.caption}</p>
          </div>
        </div>
      );

    case "x":
      return (
        <div className={cn(baseClasses, "p-4")}>
          <div className="flex gap-3">
            <div className="h-10 w-10 rounded-full bg-secondary flex-shrink-0" />
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-medium text-sm">Gaurav</span>
                <span className="text-muted-foreground text-sm">@askgauravai</span>
              </div>
              <p className="text-sm whitespace-pre-wrap">{approval.caption}</p>
            </div>
          </div>
        </div>
      );

    case "linkedin":
      return (
        <div className={baseClasses}>
          <div className="p-4 border-b border-border">
            <div className="flex items-center gap-3 mb-3">
              <div className="h-12 w-12 rounded-full bg-secondary" />
              <div>
                <p className="font-medium text-sm">Gaurav</p>
                <p className="text-xs text-muted-foreground">
                  Founder at AskGauravAI · 1st
                </p>
              </div>
            </div>
            <p className="text-sm whitespace-pre-wrap line-clamp-6">
              {approval.caption}
            </p>
          </div>
          <div className="h-48 bg-secondary flex items-center justify-center">
            <span className="text-muted-foreground text-sm">Image preview</span>
          </div>
        </div>
      );

    case "tiktok":
      return (
        <div className={cn(baseClasses, "aspect-[9/16] max-h-96 bg-secondary flex items-center justify-center relative")}>
          <span className="text-muted-foreground text-sm">Video preview</span>
          <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 to-transparent">
            <p className="text-sm text-white line-clamp-2">{approval.caption}</p>
          </div>
        </div>
      );

    case "youtube":
      return (
        <div className={baseClasses}>
          <div className="aspect-video bg-secondary flex items-center justify-center">
            <span className="text-muted-foreground text-sm">Thumbnail preview</span>
          </div>
          <div className="p-3">
            <p className="font-medium text-sm line-clamp-2">{approval.caption}</p>
            <p className="text-xs text-muted-foreground mt-1">
              AskGauravAI · Scheduled
            </p>
          </div>
        </div>
      );

    default:
      return null;
  }
}
