import { useState } from "react";
import { motion } from "framer-motion";
import { X, Send, Sparkles, FileEdit, Play, Trash2 } from "lucide-react";
import { useAppStore } from "@/store/appStore";
import { useBrandStore } from "@/store/brandStore";
import { useBrainStore, type BrainMessage, type BrainProposal } from "@/store/brainStore";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

type Proposal = BrainProposal;
type Message = BrainMessage;

const quickActions = [
  { label: "Run agent", icon: Play, prompt: "Run the " },
  { label: "Edit file", icon: FileEdit, prompt: "Edit the file at " },
  { label: "Show output", icon: Sparkles, prompt: "Show me the output from " },
];

export function TheBrain() {
  const { setBrainOpen } = useAppStore();
  const { activeBrand } = useBrandStore();
  const { scope, threads, appendMessage, updateMessage, clearThread } = useBrainStore();

  const threadKey = `${activeBrand.slug}::${scope}`;
  const messages: Message[] = threads[threadKey] ?? [];

  const [input, setInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);

  // First-message greeting (only when thread is empty)
  const displayMessages: Message[] = messages.length === 0
    ? [{
        id: "_greeting",
        role: "assistant",
        content: scope === "global"
          ? `I have full context of ${activeBrand.name}. What would you like to do?`
          : `Scoped chat. Ask anything about this agent — I have its role, last outputs, and recent runs.`,
        createdAt: 0,
      }]
    : messages;

  const handleSend = async () => {
    if (!input.trim() || isThinking) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      createdAt: Date.now(),
    };

    const newHistory = [...messages, userMessage];
    appendMessage(activeBrand.slug, scope, userMessage);
    setInput("");
    setIsThinking(true);

    try {
      const r = await apiFetch("/api/brain/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brand_slug: activeBrand.slug,
          agent_scope: scope === "global" ? null : scope,
          messages: newHistory.map((m) => ({ role: m.role, content: m.content })),
        }),
      });
      const j = await r.json();
      if (!j.success) throw new Error(j.error || "Brain unavailable");

      appendMessage(activeBrand.slug, scope, {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: j.response || "(empty response)",
        proposals: (j.proposals || []).map((p: Proposal) => ({ ...p, status: "pending" as const })),
        createdAt: Date.now(),
      });
    } catch (e) {
      appendMessage(activeBrand.slug, scope, {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Error: ${e instanceof Error ? e.message : String(e)}`,
        createdAt: Date.now(),
      });
    } finally {
      setIsThinking(false);
    }
  };

  const handleQuickAction = (prompt: string) => {
    setInput(prompt);
  };

  const handleProposalAction = async (
    msgId: string,
    proposalIdx: number,
    approve: boolean,
  ) => {
    const msg = messages.find((m) => m.id === msgId);
    if (!msg || !msg.proposals) return;
    const prop = msg.proposals[proposalIdx];
    if (!prop || prop.status !== "pending") return;

    const patchProposal = (status: BrainProposal["status"], result?: string) => {
      const updated = msg.proposals!.map((p, i) =>
        i === proposalIdx ? { ...p, status, ...(result !== undefined ? { result } : {}) } : p,
      );
      updateMessage(activeBrand.slug, scope, msgId, { proposals: updated });
    };

    if (!approve) {
      patchProposal("rejected");
      return;
    }

    patchProposal("approved");

    try {
      const r = await apiFetch("/api/brain/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: prop.kind, payload: prop.payload }),
      });
      const j = await r.json();
      patchProposal(j.success ? "executed" : "failed", j.success ? j.result : j.error);
    } catch (e) {
      patchProposal("failed", e instanceof Error ? e.message : String(e));
    }
  };

  const tokenCount = messages.reduce((acc, m) => acc + m.content.length / 4, 0);

  return (
    <motion.div
      initial={{ x: 360, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 360, opacity: 0 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="fixed right-0 top-12 bottom-0 w-[360px] border-l border-border bg-background flex flex-col"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium">The Brain</span>
          <span className="text-xs text-muted-foreground truncate">
            · {activeBrand.name}
            {scope !== "global" && (
              <button
                onClick={() => useBrainStore.getState().setScope("global")}
                className="ml-1 font-mono text-primary hover:underline"
                title="Switch back to global scope"
              >
                · {scope} ↩
              </button>
            )}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <button
              onClick={() => clearThread(activeBrand.slug, scope)}
              title="Clear this thread"
              className="flex h-6 w-6 items-center justify-center rounded hover:bg-secondary transition-colors"
            >
              <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          )}
          <button
            onClick={() => setBrainOpen(false)}
            className="flex h-6 w-6 items-center justify-center rounded hover:bg-secondary transition-colors"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {displayMessages.map((message) => (
          <div
            key={message.id}
            className={cn(
              "flex",
              message.role === "user" ? "justify-end" : "justify-start"
            )}
          >
            <div
              className={cn(
                "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                message.role === "user"
                  ? "bg-secondary text-foreground"
                  : "text-foreground"
              )}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>
              {message.proposals && message.proposals.length > 0 && (
                <div className="mt-3 space-y-2">
                  {message.proposals.map((prop, idx) => (
                    <div
                      key={idx}
                      className="rounded-md border border-border bg-card p-3 text-xs"
                    >
                      <div className="mb-2 flex items-center gap-2">
                        <span className="font-mono uppercase text-[10px] text-muted-foreground">
                          {prop.kind === "edit" ? "Propose edit" : "Propose bash"}
                        </span>
                        <span
                          className={cn(
                            "ml-auto rounded px-1.5 py-0.5 text-[10px] font-mono",
                            prop.status === "pending" && "bg-secondary text-muted-foreground",
                            prop.status === "approved" && "bg-secondary text-muted-foreground",
                            prop.status === "rejected" && "bg-destructive/20 text-destructive",
                            prop.status === "executed" && "bg-primary/20 text-primary",
                            prop.status === "failed" && "bg-destructive/20 text-destructive",
                          )}
                        >
                          {prop.status}
                        </span>
                      </div>
                      {prop.kind === "edit" ? (
                        <div className="space-y-1.5 font-mono">
                          <div className="text-muted-foreground">{prop.payload.path}</div>
                          <div className="rounded bg-destructive/10 p-1.5 text-destructive whitespace-pre-wrap break-all">
                            − {prop.payload.old_string?.slice(0, 200)}
                            {prop.payload.old_string?.length > 200 ? "…" : ""}
                          </div>
                          <div className="rounded bg-primary/10 p-1.5 text-primary whitespace-pre-wrap break-all">
                            + {prop.payload.new_string?.slice(0, 200)}
                            {prop.payload.new_string?.length > 200 ? "…" : ""}
                          </div>
                          <div className="italic text-muted-foreground">
                            {prop.payload.rationale}
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-1.5 font-mono">
                          <div className="rounded bg-secondary p-1.5 whitespace-pre-wrap break-all">
                            $ {prop.payload.command}
                          </div>
                          <div className="italic text-muted-foreground">
                            {prop.payload.rationale}
                          </div>
                        </div>
                      )}
                      {prop.result && (
                        <pre className="mt-2 max-h-32 overflow-auto rounded bg-secondary/50 p-1.5 text-[10px] font-mono whitespace-pre-wrap break-all">
                          {prop.result.slice(0, 1500)}
                        </pre>
                      )}
                      {prop.status === "pending" && (
                        <div className="mt-2 flex gap-1.5">
                          <button
                            onClick={() => handleProposalAction(message.id, idx, true)}
                            className="flex-1 rounded bg-primary px-2 py-1 text-[11px] font-medium text-primary-foreground hover:opacity-90"
                          >
                            Approve & run
                          </button>
                          <button
                            onClick={() => handleProposalAction(message.id, idx, false)}
                            className="flex-1 rounded border border-border px-2 py-1 text-[11px] hover:bg-secondary"
                          >
                            Reject
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {isThinking && (
          <div className="flex justify-start">
            <div className="text-xs text-muted-foreground font-mono animate-pulse">
              thinking…
            </div>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="border-t border-border px-4 py-2">
        <div className="flex gap-2">
          {quickActions.map((action) => (
            <button
              key={action.label}
              onClick={() => handleQuickAction(action.prompt)}
              className="flex items-center gap-1.5 rounded-full border border-border bg-card px-2.5 py-1 text-xs text-muted-foreground hover:bg-secondary transition-colors"
            >
              <action.icon className="h-3 w-3" />
              {action.label}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-border p-4">
        <div className="relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask anything..."
            className="w-full resize-none rounded-lg border border-border bg-card px-3 py-2 pr-10 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            rows={2}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isThinking}
            className="absolute bottom-2 right-2 flex h-6 w-6 items-center justify-center rounded bg-primary text-primary-foreground disabled:opacity-50 transition-opacity"
          >
            <Send className="h-3 w-3" />
          </button>
        </div>
        <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground font-mono">
          <span>⌘↵ to send · Shift+↵ for newline</span>
          <span>{Math.round(tokenCount)} tokens</span>
        </div>
      </div>
    </motion.div>
  );
}
