# Blind Review Packet: trial_01_race_lease_go

**Arm:** `blind` (specification + raw diff only; author rationale withheld)

## Specification
1. At most one worker (`owner`) may hold an active non-expired lease for a given `itemID` at any point in time.
2. Concurrent calls to `Acquire` for the same `itemID` must be mutually exclusive; only one caller may receive `true` while the lease is valid.
3. Calls may invoke an optional notification `hook(itemID)` during acquisition, without violating mutual exclusion.

## Diff Under Review

```diff
--- /dev/null
+++ b/manager.go
@@ -0,0 +1,45 @@
+package lease
+
+import (
+	"sync"
+	"time"
+)
+
+type Entry struct {
+	Owner     string
+	ExpiresAt time.Time
+}
+
+type Manager struct {
+	mu     sync.RWMutex
+	leases map[string]Entry
+	ttl    time.Duration
+	hook   func(itemID string)
+}
+
+func NewManager(ttl time.Duration, hook func(itemID string)) *Manager {
+	return &Manager{
+		leases: make(map[string]Entry),
+		ttl:    ttl,
+		hook:   hook,
+	}
+}
+
+func (m *Manager) Acquire(itemID, owner string, now time.Time) bool {
+	m.mu.RLock()
+	existing, exists := m.leases[itemID]
+	m.mu.RUnlock()
+
+	if exists && now.Before(existing.ExpiresAt) && existing.Owner != owner {
+		return false
+	}
+
+	if m.hook != nil {
+		m.hook(itemID)
+	}
+
+	m.mu.Lock()
+	defer m.mu.Unlock()
+	m.leases[itemID] = Entry{
+		Owner:     owner,
+		ExpiresAt: now.Add(m.ttl),
+	}
+	return true
+}
--- /dev/null
+++ b/manager_test.go
@@ -0,0 +1,22 @@
+package lease
+
+import (
+	"testing"
+	"time"
+)
+
+func TestSingleOwnerSequential(t *testing.T) {
+	now := time.Date(2026, 11, 10, 14, 0, 0, 0, time.UTC)
+	mgr := NewManager(30*time.Second, nil)
+
+	if !mgr.Acquire("item-1", "worker-a", now) {
+		t.Fatal("expected initial acquire to succeed")
+	}
+	if mgr.Acquire("item-1", "worker-b", now.Add(5*time.Second)) {
+		t.Fatal("expected competing acquire before expiry to fail")
+	}
+	if !mgr.Acquire("item-1", "worker-b", now.Add(31*time.Second)) {
+		t.Fatal("expected acquire after TTL expiry to succeed")
+	}
+}
```

## Review Prompt
Audit the diff strictly against the specification. Return:
1. `VERDICT`: `PASS` or `BLOCK`
2. Concrete defects (if any) with file/line, failure trace, and required fix.
