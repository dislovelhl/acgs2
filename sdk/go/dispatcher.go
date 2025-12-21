package sdk

import (
	"context"
	"fmt"
	"sync"
)

// Dispatcher handles high-concurrency message sending
type Dispatcher struct {
	client *ACGS2Client
	workers int
	queue   chan AgentMessage
	results chan *ValidationResult
	errs    chan error
	wg      sync.WaitGroup
}

// NewDispatcher creates a new concurrent message dispatcher
func NewDispatcher(client *ACGS2Client, workers int) *Dispatcher {
	return &Dispatcher{
		client:  client,
		workers: workers,
		queue:   make(chan AgentMessage, 100),
		results: make(chan *ValidationResult, 100),
		errs:    make(chan error, 100),
	}
}

// Start launches the worker pool
func (d *Dispatcher) Start(ctx context.Context) {
	for i := 0; i < d.workers; i++ {
		d.wg.Add(1)
		go d.worker(ctx)
	}
}

func (d *Dispatcher) worker(ctx context.Context) {
	defer d.wg.Done()
	for {
		select {
		case msg, ok := <-d.queue:
			if !ok {
				return
			}
			res, err := d.client.SendMessage(ctx, msg)
			if err != nil {
				d.errs <- fmt.Errorf("dispatch error for msg %s: %w", msg.ID, err)
				continue
			}
			d.results <- res
		case <-ctx.Done():
			return
		}
	}
}

// Submit adds a message to the dispatch queue
func (d *Dispatcher) Submit(msg AgentMessage) {
	d.queue <- msg
}

// Stop closes the queue and waits for workers to finish
func (d *Dispatcher) Stop() {
	close(d.queue)
	d.wg.Wait()
	close(d.results)
	close(d.errs)
}

// Results returns the results channel
func (d *Dispatcher) Results() <-chan *ValidationResult {
	return d.results
}

// Errors returns the error channel
func (d *Dispatcher) Errors() <-chan error {
	return d.errs
}
