package lease

import (
	"sync"
	"time"
)

type Entry struct {
	Owner     string
	ExpiresAt time.Time
}

type Manager struct {
	mu     sync.RWMutex
	leases map[string]Entry
	ttl    time.Duration
	hook   func(itemID string)
}

func NewManager(ttl time.Duration, hook func(itemID string)) *Manager {
	return &Manager{
		leases: make(map[string]Entry),
		ttl:    ttl,
		hook:   hook,
	}
}

func (m *Manager) Acquire(itemID, owner string, now time.Time) bool {
	m.mu.RLock()
	existing, exists := m.leases[itemID]
	m.mu.RUnlock()

	if exists && now.Before(existing.ExpiresAt) && existing.Owner != owner {
		return false
	}

	if m.hook != nil {
		m.hook(itemID)
	}

	m.mu.Lock()
	defer m.mu.Unlock()
	m.leases[itemID] = Entry{
		Owner:     owner,
		ExpiresAt: now.Add(m.ttl),
	}
	return true
}
