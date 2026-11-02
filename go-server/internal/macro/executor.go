package macro

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	"ns-controller/go-server/internal/controller"
	pb "ns-controller/go-server/proto/ns_controller"
)

// spinwaitThreshold is the window before the target where we switch from
// coarse sleep to a tight spin-wait, mirroring EonTimer's timer worker.
const spinwaitThreshold = 2 * time.Millisecond

// refreshInterval is the maximum single coarse-sleep step.
const refreshInterval = 8 * time.Millisecond

// Executor runs a Macro server-side with sub-millisecond monotonic timing.
// It writes directly to the shared State — concurrent RPCs use last-write-wins.
type Executor struct {
	macro  *pb.Macro
	state  *controller.State
	ctx    context.Context
	marks  map[string]time.Time
}

// New creates an Executor for the given macro. ctx should be cancelled to abort.
func New(macro *pb.Macro, state *controller.State, ctx context.Context) *Executor {
	return &Executor{
		macro: macro,
		state: state,
		ctx:   ctx,
		marks: make(map[string]time.Time),
	}
}

// Execute runs all macro actions in order, returning early if ctx is cancelled.
func (e *Executor) Execute() error {
	for _, action := range e.macro.Actions {
		if e.ctx.Err() != nil {
			return e.ctx.Err()
		}
		if err := e.executeAction(action); err != nil {
			slog.Error("macro action failed", "err", err)
			return err
		}
	}
	return nil
}

func (e *Executor) executeAction(action *pb.MacroAction) error {
	switch a := action.Action.(type) {
	case *pb.MacroAction_Click:
		return e.doClick(a.Click)
	case *pb.MacroAction_RepeatClick:
		return e.doRepeatClick(a.RepeatClick)
	case *pb.MacroAction_Hold:
		return e.doHold(a.Hold)
	case *pb.MacroAction_Wait:
		return e.doWait(a.Wait)
	case *pb.MacroAction_Spam:
		return e.doSpam(a.Spam)
	case *pb.MacroAction_SetMark:
		return e.doSetMark(a.SetMark)
	case *pb.MacroAction_WaitUntil:
		return e.doWaitUntil(a.WaitUntil)
	case *pb.MacroAction_SetStick:
		return e.doSetStick(a.SetStick)
	default:
		return fmt.Errorf("unknown action type: %T", action.Action)
	}
}

func (e *Executor) doClick(a *pb.ClickAction) error {
	downDur := msOr(a.DownMs, 100)
	start := time.Now()
	if a.Mark != nil {
		e.marks[a.GetMark()] = start
	}
	e.state.Press(a.Buttons...)
	if err := e.sleepUntil(start.Add(downDur)); err != nil {
		return err
	}
	e.state.Release(a.Buttons...)
	return nil
}

func (e *Executor) doRepeatClick(a *pb.RepeatClickAction) error {
	count := max(int(a.Count), 1)
	downDur := msOr(a.DownMs, 100)
	gapDur := msOr(a.GapMs, 100)
	cycleDur := downDur + gapDur

	start := time.Now()
	if a.Mark != nil {
		e.marks[a.GetMark()] = start
	}
	for i := range count {
		if e.ctx.Err() != nil {
			return e.ctx.Err()
		}
		e.state.Press(a.Buttons...)
		if err := e.sleepUntil(start.Add(time.Duration(i)*cycleDur + downDur)); err != nil {
			return err
		}
		e.state.Release(a.Buttons...)
		if i < count-1 {
			if err := e.sleepUntil(start.Add(time.Duration(i)*cycleDur + cycleDur)); err != nil {
				return err
			}
		}
	}
	return nil
}

func (e *Executor) doHold(a *pb.HoldAction) error {
	pressTime := time.Now()
	if a.Mark != nil {
		e.marks[a.GetMark()] = pressTime
	}
	e.state.Press(a.Buttons...)
	if err := e.sleepUntil(pressTime.Add(msDur(a.DurationMs))); err != nil {
		return err
	}
	e.state.Release(a.Buttons...)
	return nil
}

func (e *Executor) doWait(a *pb.WaitAction) error {
	return e.sleep(msDur(a.DurationMs))
}

func (e *Executor) doSpam(a *pb.SpamAction) error {
	intervalDur := msOr(a.IntervalMs, 100)
	downDur := time.Duration(float64(intervalDur) * 0.4)
	upDur := time.Duration(float64(intervalDur) * 0.6)
	endTime := time.Now().Add(msDur(a.DurationMs))

	for time.Now().Before(endTime) {
		if e.ctx.Err() != nil {
			e.state.Release(a.Buttons...)
			return e.ctx.Err()
		}
		e.state.Press(a.Buttons...)
		if err := e.sleep(downDur); err != nil {
			e.state.Release(a.Buttons...)
			return err
		}
		e.state.Release(a.Buttons...)
		if err := e.sleep(upDur); err != nil {
			return err
		}
	}
	return nil
}

func (e *Executor) doSetMark(a *pb.SetMarkAction) error {
	e.marks[a.Name] = time.Now()
	return nil
}

func (e *Executor) doWaitUntil(a *pb.WaitUntilAction) error {
	markTime, ok := e.marks[a.Mark]
	if !ok {
		return fmt.Errorf("wait_until: unknown mark %q", a.Mark)
	}
	return e.sleepUntil(markTime.Add(msDur(a.OffsetMs)))
}

func (e *Executor) doSetStick(a *pb.SetStickAction) error {
	e.state.SetStick(a.Stick, a.Position)
	if a.DurationMs > 0 {
		if err := e.sleep(msDur(a.DurationMs)); err != nil {
			return err
		}
		e.state.SetStick(a.Stick, &pb.Position{X: 0, Y: 0})
	}
	return nil
}

// sleep sleeps for the given duration with sub-ms precision, respecting ctx.
func (e *Executor) sleep(d time.Duration) error {
	return e.sleepUntil(time.Now().Add(d))
}

// sleepUntil sleeps until target using a hybrid coarse-sleep + spin-wait
// approach that mirrors EonTimer's timer worker for sub-millisecond precision.
func (e *Executor) sleepUntil(target time.Time) error {
	for {
		if e.ctx.Err() != nil {
			return e.ctx.Err()
		}
		remaining := time.Until(target)
		if remaining <= 0 {
			return nil
		}
		if remaining > spinwaitThreshold {
			coarse := remaining - spinwaitThreshold
			if coarse > refreshInterval {
				coarse = refreshInterval
			}
			select {
			case <-e.ctx.Done():
				return e.ctx.Err()
			case <-time.After(coarse):
			}
		} else {
			// Final 2ms: tight spin-wait for sub-ms precision.
			for time.Now().Before(target) {
				if e.ctx.Err() != nil {
					return e.ctx.Err()
				}
			}
			return nil
		}
	}
}

func msDur(ms uint32) time.Duration {
	return time.Duration(ms) * time.Millisecond
}

func msOr(ms uint32, def uint32) time.Duration {
	if ms == 0 {
		return msDur(def)
	}
	return msDur(ms)
}
