"""Sword/Shield static encounter shiny hunter.

Flow:
  1. Turbo-press A until the encounter intro dialog appears (ENCOUNTER frame).
  2. Time how long until the battle screen fully loads (POKEMON_IN_BATTLE frame).
     Shiny Pokémon have a star animation that adds ~2-3 s to this window.
  3. Maintain a running list of encounter durations.  Once enough samples exist,
     use IQR-based outlier detection: if the current duration is significantly
     longer than the baseline, the script stops for manual inspection.
  4. Otherwise: close the game (HOME → X), then rely on turbo-A in the next
     reset iteration to reopen the game, skip the title screen, load the save,
     and walk back to the encounter spot.

Prerequisites:
  - Save the game standing directly in front of (or adjacent to) the static
    Pokémon so that turboing A reliably triggers the encounter.
  - Capture reference images for ENCOUNTER and POKEMON_IN_BATTLE via the
    configurator and place them in refs/ (already done if frames.py is present).
"""

from __future__ import annotations

import math
import pathlib
import statistics
import time

from loguru import logger

from ns_controller.client import MacroBuilder, NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button
from ns_shiny_hunter.base_script import BaseScript
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.games.swsh.static.frames import SwshStaticReferenceFrames
from ns_shiny_hunter.util import is_outlier

# Number of non-shiny encounters required before outlier detection activates.
# Below this threshold every encounter is logged and added to the baseline.
_MIN_BASELINE: int = 10

# Consecutive turbo-A timeouts before the run is aborted.
_MAX_CONSECUTIVE_FAILURES: int = 3


def _synthetic_baseline(
        mean: float,
        stddev: float,
        n: int,
        min_val: float | None = None,
        max_val: float | None = None,
) -> list[float]:
    """Return *n* synthetic samples whose mean and stdev exactly match the priors.

    If *min_val* / *max_val* are provided, the sorted extremes of the generated
    samples are replaced with those values so percentile calculations reflect
    the true observed range.

    Uses the Box-Muller transform deterministically, then rescales to hit the
    target statistics exactly.
    """
    if n < 2:
        return [mean] * max(n, 1)
    # Deterministic standard-normal samples via Box-Muller
    samples: list[float] = []
    for i in range(math.ceil(n / 2)):
        u1 = (i + 1) / (math.ceil(n / 2) + 1)
        u2 = (i + 0.5) / math.ceil(n / 2)
        z0 = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
        z1 = math.sqrt(-2 * math.log(u1)) * math.sin(2 * math.pi * u2)
        samples.extend([z0, z1])
    samples = samples[:n]
    # Rescale to exactly hit target mean / stddev
    sm = statistics.mean(samples)
    ss = statistics.stdev(samples)
    samples = [(x - sm) / ss * stddev + mean for x in samples]
    # Pin observed extremes so P1/P99 are accurate
    if min_val is not None or max_val is not None:
        samples.sort()
        if min_val is not None:
            samples[0] = min_val
        if max_val is not None:
            samples[-1] = max_val
    return samples


_SEED_FILE = pathlib.Path(__file__).parent / "seed.json"


def _load_seed() -> tuple[list[float], int]:
    """Return (synthetic baseline, n) from seed.json if present, else ([], 0).

    seed.json schema::

        {"mean": 2.494, "stddev": 0.095, "n": 37, "min": 2.31, "max": 2.78}

    ``min`` and ``max`` are optional but improve percentile accuracy.
    """
    if not _SEED_FILE.exists():
        return [], 0
    import json
    seed = json.loads(_SEED_FILE.read_text())
    mean, stddev, n = seed["mean"], seed["stddev"], seed["n"]
    min_val: float | None = seed.get("min")
    max_val: float | None = seed.get("max")
    if n < _MIN_BASELINE:
        logger.warning("seed.json has n={} which is below minimum {}; ignoring seed.", n, _MIN_BASELINE)
        return [], 0
    samples = _synthetic_baseline(mean, stddev, n, min_val, max_val)
    logger.info(
        "Loaded seed.json — pre-seeded {} synthetic samples "
        "(mean={:.3f}s σ={:.3f}s min={} max={})",
        n, mean, stddev,
        f"{min_val:.3f}s" if min_val is not None else "n/a",
        f"{max_val:.3f}s" if max_val is not None else "n/a",
    )
    return samples, n


class SwshStaticScript(BaseScript):
    """Shiny hunter for a static Sword/Shield encounter.

    On startup, checks for a ``seed.json`` file next to this script containing
    ``{"mean": <float>, "stddev": <float>, "n": <int>}`` and pre-seeds the
    encounter-time baseline so outlier detection activates immediately.
    ``n`` also initialises the reset counter so logs stay accurate.

    Args:
        frame_grabber:    Live video source.
        controller:       NS controller client.
        encounter_times:  Explicit baseline (overrides seed.json if provided).
        resets:           Counter preserved across script restarts.
    """

    def __init__(
            self,
            frame_grabber: FrameGrabber,
            controller: NsControllerClient,
            encounter_times: list[float] | None = None,
            resets: int = 0,
    ) -> None:
        super().__init__(frame_grabber, controller)
        if encounter_times is not None:
            self.encounter_times: list[float] = encounter_times
            self.resets = resets
        else:
            seeded, n = _load_seed()
            self.encounter_times = seeded
            self.resets = resets or n

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        logger.info(
            "SWSH static shiny hunter started — baseline needed: {} encounters",
            _MIN_BASELINE,
        )
        consecutive_failures = 0
        try:
            while True:
                self.resets += 1
                logger.info("Reset #{} — turboing A to trigger encounter…", self.resets)

                # Turbo-A through title screen, save load, and dialog until the
                # encounter intro frame appears.
                if not self.click_until(SwshStaticReferenceFrames.ENCOUNTER, Button.A, post_delay=0.15):
                    consecutive_failures += 1
                    logger.warning(
                        "Turbo-A timed out reaching encounter ({}/{} consecutive failures) — resetting.",
                        consecutive_failures,
                        _MAX_CONSECUTIVE_FAILURES,
                    )
                    if consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                        logger.error(
                            "{} consecutive failures — aborting run and sleeping console.",
                            _MAX_CONSECUTIVE_FAILURES,
                        )
                        self._sleep_console()
                        break
                    self._reset_game()
                    continue

                consecutive_failures = 0
                appeared_at = time.perf_counter()
                logger.info("Encounter appeared — waiting for Pokémon in battle…")

                # No inputs during the transition; just wait for the battle screen.
                self.wait_for(SwshStaticReferenceFrames.POKEMON_IN_BATTLE, timeout=60.0)
                delta_t = time.perf_counter() - appeared_at

                self._log_encounter(delta_t)

                if self._is_shiny(delta_t):
                    logger.info(
                        "🌟 Possible shiny after {} resets! Encounter time: {:.3f}s"
                        " — capturing clip then sleeping console.",
                        self.resets,
                        delta_t,
                    )
                    self._capture_and_sleep()
                    break

                self.encounter_times.append(delta_t)
                self._reset_game()

        except KeyboardInterrupt:
            logger.info("Interrupted after {} resets.", self.resets)
            self._log_stats()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _is_shiny(self, delta_t: float) -> bool:
        """Return True if *delta_t* looks like a shiny encounter.

        Requires at least *_MIN_BASELINE* samples; before that every encounter
        is treated as non-shiny and added to the baseline.
        """
        n = len(self.encounter_times)
        if n < _MIN_BASELINE:
            logger.info("  Baseline {}/{} — skipping outlier check.", n + 1, _MIN_BASELINE)
            return False
        return is_outlier(delta_t, self.encounter_times)

    def _reset_game(self) -> None:
        """Close the game via HOME → X.  The next iteration's turbo-A reopens it."""
        logger.info("  Resetting game.")
        self.controller.exec_macro(
            MacroBuilder()
            .click(Button.HOME, down_ms=200)
            .wait(1250)
            .click(Button.X)
            .wait(500)
            .build()
        )

    def _sleep_console(self) -> None:
        """Put the console to sleep via long-press HOME → A."""
        self.controller.exec_macro(
            MacroBuilder()
            .click(Button.HOME, down_ms=800)
            .wait(1000)
            .click(Button.A)
            .build()
        )
        logger.info("  Console sleeping.")

    def _capture_and_sleep(self) -> None:
        """Wait 10s (shiny animation plays), trigger Switch screen recording,
        wait 5s for the save to complete, then put the console to sleep."""
        logger.info("  Waiting 10s before capturing clip…")
        time.sleep(10.0)
        logger.info("  Long-pressing CAPTURE button to save clip…")
        self.controller.exec_macro(
            MacroBuilder()
            .click(Button.CAPTURE, down_ms=2000)
            .wait(5000)
            .build()
        )
        logger.info("  Clip saved — putting console to sleep.")
        self._sleep_console()
        logger.info("  Hunt complete after {} resets.", self.resets)
        self._log_stats()

    def _log_encounter(self, delta_t: float) -> None:
        n = len(self.encounter_times)
        if n >= 2:
            logger.info(
                "  Encounter time: {:.3f}s  (mean={:.3f}s  σ={:.3f}  min={:.3f}s  max={:.3f}s  n={})",
                delta_t,
                statistics.mean(self.encounter_times),
                statistics.stdev(self.encounter_times),
                min(self.encounter_times),
                max(self.encounter_times),
                n,
            )
        else:
            logger.info("  Encounter time: {:.3f}s  (collecting baseline)", delta_t)

    def _log_stats(self) -> None:
        n = len(self.encounter_times)
        if n < 2:
            return
        logger.info(
            "Final stats — n={}  mean={:.3f}s  σ={:.3f}s  min={:.3f}s  max={:.3f}s",
            n,
            statistics.mean(self.encounter_times),
            statistics.stdev(self.encounter_times),
            min(self.encounter_times),
            max(self.encounter_times),
        )
