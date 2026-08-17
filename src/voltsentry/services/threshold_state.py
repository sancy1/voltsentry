# """
# FILE: src/voltsentry/services/threshold_state.py
# PATH: voltsentry/src/voltsentry/services/threshold_state.py
# DESCRIPTION: Threshold state machine with hysteresis for alarm triggering
# PHASE: 3.1 - Threshold State Machine

# DISCIPLINES:
# - 0.1 Logging Standard: INFO on state transitions, DEBUG on state checks
# - 0.2 Error Handling: Validate inputs, no bare except
# - 0.4 Fallback Standard: Default to NORMAL state on invalid input
# """

# from dataclasses import dataclass
# from enum import Enum, auto
# from typing import Optional, Callable

# from ..core.constants import HYSTERESIS_MARGIN
# from ..core.logging_config import get_logger
# from ..core.decorators import log_entry_exit

# logger = get_logger(__name__)


# class ThresholdState(Enum):
#     """Battery threshold states."""
#     NORMAL = "normal"
#     APPROACHING_FULL = "approaching_full"
#     FULL_ALARM = "full_alarm"
#     APPROACHING_LOW = "approaching_low"
#     LOW_ALARM = "low_alarm"
#     CRITICAL_LOW = "critical_low"


# @dataclass
# class ThresholdConfig:
#     """Configuration for threshold state machine."""
#     high_threshold: int = 85      # Stop charging at this %
#     low_threshold: int = 20       # Start charging at this %
#     critical_threshold: int = 5   # Critical low at this %
#     hysteresis: int = HYSTERESIS_MARGIN


# class ThresholdStateMachine:
#     """
#     State machine for battery threshold management with hysteresis.

#     States:
#     - NORMAL: Default state, no alarms active
#     - APPROACHING_FULL: Charging, below high threshold
#     - FULL_ALARM: Reached high threshold while charging
#     - APPROACHING_LOW: Discharging, above low threshold
#     - LOW_ALARM: Reached low threshold while discharging
#     - CRITICAL_LOW: Below 5%, highest priority

#     Hysteresis prevents alarm flapping at threshold boundaries.
#     """

#     def __init__(
#         self,
#         config: Optional[ThresholdConfig] = None,
#         on_state_change: Optional[Callable[[ThresholdState, ThresholdState], None]] = None,
#     ):
#         """
#         Initialize the state machine.

#         Args:
#             config: Threshold configuration (uses defaults if None)
#             on_state_change: Callback when state changes (old, new)
#         """
#         self.config = config or ThresholdConfig()
#         self._current_state = ThresholdState.NORMAL
#         self._previous_state = ThresholdState.NORMAL
#         self._on_state_change = on_state_change
#         self._last_percent: Optional[int] = None
#         self._last_charging: Optional[bool] = None

#         logger.info(
#             "ThresholdStateMachine initialized: high=%d%%, low=%d%%, critical=%d%%, hysteresis=%d%%",
#             self.config.high_threshold,
#             self.config.low_threshold,
#             self.config.critical_threshold,
#             self.config.hysteresis,
#         )

#     @property
#     def current_state(self) -> ThresholdState:
#         """Get the current state."""
#         return self._current_state

#     @property
#     def is_alarm_active(self) -> bool:
#         """Check if any alarm state is active."""
#         return self._current_state in (
#             ThresholdState.FULL_ALARM,
#             ThresholdState.LOW_ALARM,
#             ThresholdState.CRITICAL_LOW,
#         )

#     @log_entry_exit()
#     def update(self, percent: int, is_charging: bool) -> ThresholdState:
#         """
#         Update the state machine with new battery data.

#         Args:
#             percent: Current battery percentage (0-100)
#             is_charging: True if battery is charging

#         Returns:
#             New state after update
#         """
#         logger.debug("State update check: percent=%s, is_charging=%s", percent, is_charging)

#         # Validate input
#         if not isinstance(percent, (int, float)):
#             logger.warning("Invalid percent type '%s', defaulting to NORMAL state", type(percent))
#             return self._fallback_to_normal()

#         percent_int = int(percent)
#         if not 0 <= percent_int <= 100:
#             logger.warning("Invalid percent value: %d, clamping to 0-100", percent_int)
#             percent_int = max(0, min(100, percent_int))

#         is_charging_bool = bool(is_charging)

#         # Store previous values
#         self._previous_state = self._current_state
#         self._last_percent = percent_int
#         self._last_charging = is_charging_bool

#         # Check hysteresis first
#         if self._should_stay_in_alarm_due_to_hysteresis(percent_int, is_charging_bool):
#             return self._current_state

#         # Determine new candidate state
#         new_state = self._determine_state(percent_int, is_charging_bool)

#         # Handle transition
#         if new_state != self._current_state:
#             old_state = self._current_state
#             self._current_state = new_state
#             logger.info(
#                 "State transition: %s → %s (percent=%d%%, charging=%s)",
#                 old_state.value,
#                 new_state.value,
#                 percent_int,
#                 is_charging_bool,
#             )

#             if self._on_state_change:
#                 try:
#                     self._on_state_change(old_state, new_state)
#                 except Exception as e:
#                     logger.error("State change callback failed: %s", e)

#         return self._current_state

#     def _determine_state(self, percent: int, is_charging: bool) -> ThresholdState:
#         """
#         Determine the appropriate state based on current values.

#         Priority order (highest first):
#         1. CRITICAL_LOW - safety critical
#         2. LOW_ALARM - low battery
#         3. FULL_ALARM - full charge
#         4. APPROACHING states
#         5. NORMAL
#         """
#         # CRITICAL_LOW: highest priority, regardless of charging state
#         if percent < self.config.critical_threshold:
#             return ThresholdState.CRITICAL_LOW

#         # LOW_ALARM: when discharging and at/below low threshold
#         if not is_charging and percent <= self.config.low_threshold:
#             return ThresholdState.LOW_ALARM

#         # FULL_ALARM: when charging and at/above high threshold
#         if is_charging and percent >= self.config.high_threshold:
#             return ThresholdState.FULL_ALARM

#         # When charging and below high threshold, state is APPROACHING_FULL
#         if is_charging:
#             return ThresholdState.APPROACHING_FULL

#         # When discharging and above low threshold, state is APPROACHING_LOW
#         if not is_charging:
#             return ThresholdState.APPROACHING_LOW

#         return ThresholdState.NORMAL

#     def _should_stay_in_alarm_due_to_hysteresis(self, percent: int, is_charging: bool) -> bool:
#         """
#         Check if hysteresis should keep the current alarm active.
#         """
#         config = self.config

#         # Check hysteresis for FULL_ALARM
#         if self._current_state == ThresholdState.FULL_ALARM and is_charging:
#             if percent >= (config.high_threshold - config.hysteresis):
#                 return True  # Stay in FULL_ALARM

#         # Check hysteresis for LOW_ALARM
#         if self._current_state == ThresholdState.LOW_ALARM and not is_charging:
#             if percent <= (config.low_threshold + config.hysteresis):
#                 return True  # Stay in LOW_ALARM

#         return False

#     def _fallback_to_normal(self) -> ThresholdState:
#         """Fallback helper to transition to NORMAL on unrecoverable input errors."""
#         if self._current_state != ThresholdState.NORMAL:
#             logger.info("Fallback standard applied: resetting from %s to NORMAL", self._current_state.value)
#             self.reset()
#         return ThresholdState.NORMAL

#     def reset(self) -> None:
#         """Reset the state machine to NORMAL state."""
#         old_state = self._current_state
#         self._current_state = ThresholdState.NORMAL
#         self._previous_state = ThresholdState.NORMAL

#         if old_state != self._current_state:
#             logger.info("State machine reset: %s → NORMAL", old_state.value)
#             if self._on_state_change:
#                 try:
#                     self._on_state_change(old_state, self._current_state)
#                 except Exception as e:
#                     logger.error("State change callback failed: %s", e)

#     def get_state_info(self) -> dict:
#         """Get current state information."""
#         return {
#             "current_state": self._current_state.value,
#             "previous_state": self._previous_state.value,
#             "is_alarm_active": self.is_alarm_active,
#             "last_percent": self._last_percent,
#             "last_charging": self._last_charging,
#             "config": {
#                 "high_threshold": self.config.high_threshold,
#                 "low_threshold": self.config.low_threshold,
#                 "critical_threshold": self.config.critical_threshold,
#                 "hysteresis": self.config.hysteresis,
#             },
#         }

#     def __repr__(self) -> str:
#         return f"<ThresholdStateMachine state={self._current_state.value}>"




































"""
FILE: src/voltsentry/services/threshold_state.py
PATH: voltsentry/src/voltsentry/services/threshold_state.py
DESCRIPTION: Threshold state machine with hysteresis for alarm triggering
PHASE: 3.1 - Threshold State Machine

DISCIPLINES:
- 0.1 Logging Standard: INFO on state transitions, DEBUG on state checks
- 0.2 Error Handling: Validate inputs, no bare except
- 0.4 Fallback Standard: Default to NORMAL state on invalid input
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable

from ..core.constants import HYSTERESIS_MARGIN
from ..core.logging_config import get_logger
from ..core.decorators import log_entry_exit

logger = get_logger(__name__)


class ThresholdState(Enum):
    """Battery threshold states."""
    NORMAL = "normal"
    APPROACHING_FULL = "approaching_full"
    FULL_ALARM = "full_alarm"
    APPROACHING_LOW = "approaching_low"
    LOW_ALARM = "low_alarm"
    CRITICAL_LOW = "critical_low"


@dataclass
class ThresholdConfig:
    """Configuration for threshold state machine."""
    high_threshold: int = 85      # Stop charging at this %
    low_threshold: int = 20       # Start charging at this %
    critical_threshold: int = 5   # Critical low at this %
    hysteresis: int = HYSTERESIS_MARGIN


class ThresholdStateMachine:
    """
    State machine for battery threshold management with hysteresis.

    States:
    - NORMAL: Default state, no alarms active
    - APPROACHING_FULL: Charging, within hysteresis margin below high threshold
    - FULL_ALARM: Reached high threshold while charging
    - APPROACHING_LOW: Discharging, within hysteresis margin above low threshold
    - LOW_ALARM: Reached low threshold while discharging
    - CRITICAL_LOW: Below critical threshold, highest priority

    Hysteresis prevents alarm flapping at threshold boundaries.
    """

    def __init__(
        self,
        config: Optional[ThresholdConfig] = None,
        on_state_change: Optional[Callable[[ThresholdState, ThresholdState], None]] = None,
    ):
        """
        Initialize the state machine.

        Args:
            config: Threshold configuration (uses defaults if None)
            on_state_change: Callback when state changes (old, new)
        """
        self.config = config or ThresholdConfig()
        self._current_state = ThresholdState.NORMAL
        self._previous_state = ThresholdState.NORMAL
        self._on_state_change = on_state_change
        self._last_percent: Optional[int] = None
        self._last_charging: Optional[bool] = None

        # Validate initial config - fallback to default if invalid
        if not self._validate_config(self.config):
            logger.warning("Invalid configuration supplied; resetting to default ThresholdConfig.")
            self.config = ThresholdConfig()

        logger.info(
            "ThresholdStateMachine initialized: high=%d%%, low=%d%%, critical=%d%%, hysteresis=%d%%",
            self.config.high_threshold,
            self.config.low_threshold,
            self.config.critical_threshold,
            self.config.hysteresis,
        )

    def _validate_config(self, config: ThresholdConfig) -> bool:
        """
        Validate threshold hierarchy:
        0 <= critical_threshold < low_threshold < high_threshold <= 100
        """
        if not (0 <= config.critical_threshold < config.low_threshold < config.high_threshold <= 100):
            logger.error(
                "Invalid threshold hierarchy: crit=%d, low=%d, high=%d. "
                "Must satisfy: 0 <= crit < low < high <= 100",
                config.critical_threshold,
                config.low_threshold,
                config.high_threshold,
            )
            return False

        if not (0 <= config.hysteresis <= 20):
            logger.error("Invalid hysteresis margin: %d. Must be between 0 and 20.", config.hysteresis)
            return False

        return True

    @property
    def current_state(self) -> ThresholdState:
        """Get the current state."""
        return self._current_state

    @property
    def is_alarm_active(self) -> bool:
        """Check if any alarm state is active."""
        return self._current_state in (
            ThresholdState.FULL_ALARM,
            ThresholdState.LOW_ALARM,
            ThresholdState.CRITICAL_LOW,
        )

    def update_config(
        self,
        high_threshold: Optional[int] = None,
        low_threshold: Optional[int] = None,
        critical_threshold: Optional[int] = None,
        hysteresis: Optional[int] = None,
    ) -> bool:
        """
        Dynamically update threshold settings at runtime.

        Returns:
            True if update was applied, False if validation failed
        """
        def _safe_int_cast(val, fallback: int) -> int:
            if val is None:
                return fallback
            try:
                return int(val)
            except (ValueError, TypeError):
                return fallback

        new_high = _safe_int_cast(high_threshold, self.config.high_threshold)
        new_low = _safe_int_cast(low_threshold, self.config.low_threshold)
        new_crit = _safe_int_cast(critical_threshold, self.config.critical_threshold)
        new_hyst = _safe_int_cast(hysteresis, self.config.hysteresis)

        candidate_config = ThresholdConfig(
            high_threshold=new_high,
            low_threshold=new_low,
            critical_threshold=new_crit,
            hysteresis=new_hyst,
        )

        if not self._validate_config(candidate_config):
            return False

        self.config = candidate_config

        logger.info(
            "ThresholdStateMachine config updated: high=%d%%, low=%d%%, critical=%d%%, hysteresis=%d",
            self.config.high_threshold,
            self.config.low_threshold,
            self.config.critical_threshold,
            self.config.hysteresis,
        )

        # Immediate re-evaluation with last known sensor values
        if self._last_percent is not None and self._last_charging is not None:
            logger.debug(
                "Re-evaluating state with updated thresholds: percent=%d%%, charging=%s",
                self._last_percent,
                self._last_charging,
            )
            self.update(self._last_percent, self._last_charging)

        return True

    @log_entry_exit()
    def update(self, percent: int, is_charging: bool) -> ThresholdState:
        """
        Update state machine with new battery percentage and charging state.
        """
        logger.debug("State update evaluation: percent=%s%%, is_charging=%s", percent, is_charging)

        # Validate input types
        if not isinstance(percent, (int, float)):
            logger.warning("Invalid percent type '%s'", type(percent))
            return self._fallback_to_normal()

        percent_int = int(percent)
        if not (0 <= percent_int <= 100):
            logger.warning("Out of range percent value: %d. Clamping to [0, 100].", percent_int)
            percent_int = max(0, min(100, percent_int))

        is_charging_bool = bool(is_charging)

        # Record history
        self._previous_state = self._current_state
        self._last_percent = percent_int
        self._last_charging = is_charging_bool

        # Determine structural target state
        new_state = self._determine_state(percent_int, is_charging_bool)

        # Evaluate hysteresis hold
        if self._should_stay_in_current_state(percent_int, is_charging_bool, new_state):
            logger.debug(
                "Hysteresis active: maintaining %s at %d%%",
                self._current_state.value,
                percent_int,
            )
            return self._current_state

        # Apply state transition
        if new_state != self._current_state:
            old_state = self._current_state
            self._current_state = new_state
            logger.info(
                "State transition: %s → %s (percent=%d%%, charging=%s)",
                old_state.value,
                new_state.value,
                percent_int,
                is_charging_bool,
            )

            if self._on_state_change:
                try:
                    self._on_state_change(old_state, new_state)
                except Exception as e:
                    logger.error("State change callback execution failed: %s", e)

        return self._current_state

    def _determine_state(self, percent: int, is_charging: bool) -> ThresholdState:
        """
        Evaluates battery metrics against rules in order of priority:
        1. CRITICAL_LOW (< critical_threshold)
        2. FULL_ALARM (is_charging and >= high_threshold)
        3. LOW_ALARM (not is_charging and <= low_threshold)
        4. APPROACHING_FULL (is_charging and >= high_threshold - hysteresis)
        5. APPROACHING_LOW (not is_charging and <= low_threshold + hysteresis)
        6. NORMAL
        """
        config = self.config

        if percent < config.critical_threshold:
            return ThresholdState.CRITICAL_LOW

        if is_charging and percent >= config.high_threshold:
            return ThresholdState.FULL_ALARM

        if not is_charging and percent <= config.low_threshold:
            return ThresholdState.LOW_ALARM

        if is_charging and percent >= (config.high_threshold - config.hysteresis):
            return ThresholdState.APPROACHING_FULL

        if not is_charging and percent <= (config.low_threshold + config.hysteresis):
            return ThresholdState.APPROACHING_LOW

        return ThresholdState.NORMAL

    def _should_stay_in_current_state(
        self,
        percent: int,
        is_charging: bool,
        new_state: ThresholdState,
    ) -> bool:
        """Check if active hysteresis window holds the current state."""
        current = self._current_state
        config = self.config

        if new_state == current:
            return True

        if current == ThresholdState.CRITICAL_LOW or new_state == ThresholdState.CRITICAL_LOW:
            return False

        if current == ThresholdState.FULL_ALARM:
            if is_charging and percent >= (config.high_threshold - config.hysteresis):
                return True

        if current == ThresholdState.LOW_ALARM:
            if not is_charging and percent <= (config.low_threshold + config.hysteresis):
                return True

        return False

    def _fallback_to_normal(self) -> ThresholdState:
        """Helper to safely fall back to NORMAL state during input failures."""
        if self._current_state != ThresholdState.NORMAL:
            logger.info("Fallback invoked: resetting state from %s to NORMAL", self._current_state.value)
            self.reset()
        return ThresholdState.NORMAL

    def reset(self) -> None:
        """Reset the state machine to NORMAL state."""
        old_state = self._current_state
        self._current_state = ThresholdState.NORMAL
        self._previous_state = ThresholdState.NORMAL

        if old_state != self._current_state:
            logger.info("State machine reset: %s → NORMAL", old_state.value)
            if self._on_state_change:
                try:
                    self._on_state_change(old_state, self._current_state)
                except Exception as e:
                    logger.error("State change callback execution failed: %s", e)

    def get_state_info(self) -> dict:
        """Get current state information snapshot."""
        return {
            "current_state": self._current_state.value,
            "previous_state": self._previous_state.value,
            "is_alarm_active": self.is_alarm_active,
            "last_percent": self._last_percent,
            "last_charging": self._last_charging,
            "config": {
                "high_threshold": self.config.high_threshold,
                "low_threshold": self.config.low_threshold,
                "critical_threshold": self.config.critical_threshold,
                "hysteresis": self.config.hysteresis,
            },
        }

    def __repr__(self) -> str:
        return f"<ThresholdStateMachine state={self._current_state.value}>"
    