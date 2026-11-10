package lease

import (
	"sync"
	"testing"
	"time"
)

func TestSingleOwnerSequential(t *testing.T) {
	now := time.Date(2026, 11, 10, 14, 0, 0, 0, time.UTC)
	mgr := NewManager(30*time.Second, nil)

	if !mgr.Acquire("item-1", "worker-a", now) {
		t.Fatal("expected initial acquire to succeed")
	}
	if mgr.Acquire("item-1", "worker-b", now.Add(5*time.Second)) {
		t.Fatal("expected competing acquire before expiry to fail")
	}
	if !mgr.Acquire("item-1", "worker-b", now.Add(31*time.Second)) {
		t.Fatal("expected acquire after TTL expiry to succeed")
	}
}

func TestReproConcurrentDoubleAcquire(t *testing.T) {
	now := time.Date(2026, 11, 10, 14, 0, 0, 0, time.UTC)
	ready := make(chan struct{})
	var arrived sync.WaitGroup
	arrived.Add(2)

	mgr := NewManager(30*time.Second, func(_ string) {
		arrived.Done()
		<-ready
	})

	var mu sync.Mutex
	winners := 0
	var done sync.WaitGroup
	done.Add(2)

	go func() {
		defer done.Done()
		if mgr.Acquire("item-race", "worker-a", now) {
			mu.Lock()
			winners++
			mu.Unlock()
		}
	}()
	go func() {
		defer done.Done()
		if mgr.Acquire("item-race", "worker-b", now) {
			mu.Lock()
			winners++
			mu.Unlock()
		}
	}()

	arrived.Wait()
	close(ready)
	done.Wait()

	if winners != 1 {
		t.Fatalf("seeded defect reproduced: expected 1 lease winner, got %d", winners)
	}
}
