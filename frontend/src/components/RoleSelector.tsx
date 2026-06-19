"use client";

type Role = "front_desk" | "vet_tech" | "vet" | "regional_manager";

interface RoleSelectorProps {
  role: Role;
  onRoleChange: (role: Role) => void;
}

const ROLES: Array<{ id: Role; label: string; icon: string }> = [
  { id: "front_desk",       label: "Front Desk",       icon: "🖥️" },
  { id: "vet_tech",         label: "Vet Tech",         icon: "🔬" },
  { id: "vet",              label: "Veterinarian",     icon: "🩺" },
  { id: "regional_manager", label: "Regional Mgr",    icon: "🗺️" },
];

export default function RoleSelector({ role, onRoleChange }: RoleSelectorProps) {
  return (
    <div
      style={{
        display: "flex",
        gap: "4px",
        background: "rgba(9,9,11,0.8)",
        border: "1px solid rgba(63,63,70,0.5)",
        borderRadius: "12px",
        padding: "4px",
      }}
    >
      {ROLES.map((r) => {
        const isActive = r.id === role;
        return (
          <button
            key={r.id}
            id={`role-btn-${r.id}`}
            onClick={() => onRoleChange(r.id)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 12px",
              borderRadius: "8px",
              border: "none",
              cursor: "pointer",
              fontSize: "0.75rem",
              fontWeight: isActive ? 700 : 500,
              fontFamily: "inherit",
              transition: "all 0.2s ease",
              background: isActive
                ? "linear-gradient(135deg, rgba(99,102,241,0.25) 0%, rgba(59,130,246,0.15) 100%)"
                : "transparent",
              color: isActive ? "#c7d2fe" : "#71717a",
              boxShadow: isActive ? "0 1px 8px rgba(99,102,241,0.2)" : "none",
              borderBottom: isActive ? "1px solid rgba(99,102,241,0.4)" : "1px solid transparent",
              whiteSpace: "nowrap",
            }}
          >
            <span style={{ fontSize: "0.85rem" }}>{r.icon}</span>
            {r.label}
          </button>
        );
      })}
    </div>
  );
}
