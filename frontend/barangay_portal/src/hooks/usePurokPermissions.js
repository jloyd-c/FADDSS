import { useMemo } from 'react'
import useAuthStore from '../store/authStore'

/**
 * usePurokPermissions
 *
 * Returns helpers derived from the logged-in user's assigned_puroks list.
 * For ADMIN / SUPER_ADMIN the helpers always return true (global access).
 * For STAFF they check the specific purok permission flags.
 * For RESIDENT / unauthenticated they always return false.
 *
 * Usage:
 *   const { canView, canCreate, canEdit, canExport, assignedPuroks } = usePurokPermissions()
 *   if (canCreate(purok.id)) { ... }
 */
export function usePurokPermissions() {
  const user = useAuthStore((s) => s.user)

  return useMemo(() => {
    if (!user) {
      return _noneAccess([])
    }

    const role = user.role

    if (role === 'SUPER_ADMIN' || role === 'ADMIN') {
      return _adminAccess()
    }

    if (role === 'STAFF') {
      const puroks = user.assigned_puroks ?? []
      return _staffAccess(puroks)
    }

    return _noneAccess([])
  }, [user])
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function _noneAccess(assignedPuroks) {
  return {
    assignedPuroks,
    isGlobalAccess: false,
    canView:           () => false,
    canCreate:         () => false,
    canEdit:           () => false,
    canDelete:         () => false,
    canExport:         () => false,
    canViewAuditLogs:  () => false,
    purokIdsFor:       () => [],
  }
}

function _adminAccess() {
  return {
    assignedPuroks:   null,   // null signals "all puroks"
    isGlobalAccess:   true,
    canView:          () => true,
    canCreate:        () => true,
    canEdit:          () => true,
    canDelete:        () => true,
    canExport:        () => true,
    canViewAuditLogs: () => true,
    // Returns null = "no purok restriction" — callers can omit the filter
    purokIdsFor:      () => null,
  }
}

function _staffAccess(puroks) {
  const byId = Object.fromEntries(puroks.map((p) => [p.purok_id, p]))

  function check(flag, purokId) {
    if (purokId === undefined) {
      // No specific purok — true if they have the flag on ANY purok
      return puroks.some((p) => p[flag])
    }
    return byId[purokId]?.[flag] ?? false
  }

  return {
    assignedPuroks:   puroks,
    isGlobalAccess:   false,
    canView:          (purokId) => check('can_view',            purokId),
    canCreate:        (purokId) => check('can_create',          purokId),
    canEdit:          (purokId) => check('can_edit',            purokId),
    canDelete:        (purokId) => check('can_delete',          purokId),
    canExport:        (purokId) => check('can_export',          purokId),
    canViewAuditLogs: (purokId) => check('can_view_audit_logs', purokId),
    // Returns the list of purok IDs the staff can use for the given flag
    purokIdsFor: (flag) => puroks.filter((p) => p[flag]).map((p) => p.purok_id),
  }
}
