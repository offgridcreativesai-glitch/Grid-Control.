import { useState } from "react"
import { Users, UserPlus, Shield, Eye, Pencil, Trash2, Loader2, AlertCircle, Mail } from "lucide-react"
import { cn } from "@/lib/utils"
import { useTeamMembers, useInviteMember, useUpdateRole, useRemoveMember, type TeamMember } from "@/hooks/useTeam"
import { useAuthStore } from "@/store/authStore"

const roleConfig = {
  admin: { label: "Admin", icon: Shield, color: "text-primary", bg: "bg-primary/10" },
  editor: { label: "Editor", icon: Pencil, color: "text-blue-400", bg: "bg-blue-500/10" },
  viewer: { label: "Viewer", icon: Eye, color: "text-muted-foreground", bg: "bg-muted/50" },
}

function RoleBadge({ role }: { role: string }) {
  const cfg = roleConfig[role as keyof typeof roleConfig] ?? roleConfig.viewer
  const Icon = cfg.icon
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium", cfg.bg, cfg.color)}>
      <Icon className="h-3 w-3" />
      {cfg.label}
    </span>
  )
}

function MemberRow({
  member,
  isCurrentUser,
}: {
  member: TeamMember
  isCurrentUser: boolean
}) {
  const updateRole = useUpdateRole()
  const removeMember = useRemoveMember()
  const [confirmRemove, setConfirmRemove] = useState(false)

  const handleRoleChange = (newRole: string) => {
    updateRole.mutate({ userId: member.user_id, role: newRole })
  }

  return (
    <div className="flex items-center justify-between px-4 py-3">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-secondary text-sm font-medium text-foreground">
          {(member.profiles?.display_name || member.profiles?.email || "?")[0].toUpperCase()}
        </div>
        <div>
          <p className="text-sm font-medium text-foreground">
            {member.profiles?.display_name || "Unnamed"}
            {isCurrentUser && <span className="ml-1.5 text-xs text-muted-foreground">(you)</span>}
          </p>
          <p className="text-xs text-muted-foreground">{member.profiles?.email}</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {!isCurrentUser ? (
          <>
            <select
              value={member.role}
              onChange={(e) => handleRoleChange(e.target.value)}
              disabled={updateRole.isPending}
              className="rounded-md border border-border bg-card px-2 py-1 text-xs text-foreground"
            >
              <option value="admin">Admin</option>
              <option value="editor">Editor</option>
              <option value="viewer">Viewer</option>
            </select>

            {confirmRemove ? (
              <div className="flex items-center gap-1">
                <button
                  onClick={() => {
                    removeMember.mutate(member.user_id)
                    setConfirmRemove(false)
                  }}
                  disabled={removeMember.isPending}
                  className="rounded px-2 py-1 text-xs font-medium text-red-400 hover:bg-red-500/10"
                >
                  Confirm
                </button>
                <button
                  onClick={() => setConfirmRemove(false)}
                  className="rounded px-2 py-1 text-xs text-muted-foreground hover:bg-secondary"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmRemove(true)}
                className="rounded p-1.5 text-muted-foreground hover:bg-red-500/10 hover:text-red-400 transition-colors"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </>
        ) : (
          <RoleBadge role={member.role} />
        )}
      </div>
    </div>
  )
}

export function TeamPage() {
  const { user } = useAuthStore()
  const { data: members, isLoading } = useTeamMembers()
  const inviteMember = useInviteMember()
  const [email, setEmail] = useState("")
  const [role, setRole] = useState("editor")
  const [showInvite, setShowInvite] = useState(false)

  const handleInvite = (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return
    inviteMember.mutate(
      { email: email.trim(), role },
      {
        onSuccess: () => {
          setEmail("")
          setShowInvite(false)
        },
      }
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Team</h1>
          <p className="text-sm text-muted-foreground">
            Manage who has access to this brand.
          </p>
        </div>
        <button
          onClick={() => setShowInvite(!showInvite)}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <UserPlus className="h-4 w-4" />
          Invite
        </button>
      </div>

      {/* Invite Form */}
      {showInvite && (
        <form onSubmit={handleInvite} className="rounded-xl border border-primary/20 bg-primary/5 p-4">
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                Email address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="teammate@company.com"
                  className="w-full rounded-lg border border-border bg-card py-2 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
                  required
                />
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted-foreground">
                Role
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground"
              >
                <option value="admin">Admin</option>
                <option value="editor">Editor</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>
            <button
              type="submit"
              disabled={inviteMember.isPending}
              className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {inviteMember.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Send Invite"
              )}
            </button>
          </div>

          {inviteMember.isError && (
            <div className="mt-3 flex items-center gap-2 text-xs text-red-400">
              <AlertCircle className="h-3.5 w-3.5" />
              {inviteMember.error?.message || "Failed to send invite"}
            </div>
          )}
        </form>
      )}

      {/* Role Legend */}
      <div className="flex items-center gap-4">
        {Object.entries(roleConfig).map(([key, cfg]) => (
          <div key={key} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <cfg.icon className={cn("h-3.5 w-3.5", cfg.color)} />
            <span className="font-medium">{cfg.label}</span>
            <span>
              {key === "admin" && "— full access"}
              {key === "editor" && "— can approve & edit"}
              {key === "viewer" && "— read only"}
            </span>
          </div>
        ))}
      </div>

      {/* Members List */}
      <div className="rounded-xl border border-border bg-card">
        <div className="flex items-center gap-2 border-b border-border px-4 py-3">
          <Users className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">
            Members ({members?.length ?? 0})
          </span>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : members && members.length > 0 ? (
          <div className="divide-y divide-border">
            {members.map((member) => (
              <MemberRow
                key={member.id}
                member={member}
                isCurrentUser={user?.id === member.user_id}
              />
            ))}
          </div>
        ) : (
          <div className="py-12 text-center text-sm text-muted-foreground">
            No team members yet. Invite someone to get started.
          </div>
        )}
      </div>
    </div>
  )
}
