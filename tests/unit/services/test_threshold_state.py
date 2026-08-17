"""
FILE: tests/unit/services/test_threshold_state.py
PATH: voltsentry/tests/unit/services/test_threshold_state.py
DESCRIPTION: Unit tests for ThresholdStateMachine
PHASE: 3.5 - Unit Tests
"""

import pytest

from voltsentry.services.threshold_state import (
    ThresholdStateMachine,
    ThresholdConfig,
    ThresholdState,
)


class TestThresholdStateMachine:
    """Test suite for ThresholdStateMachine."""

    @pytest.fixture
    def config(self) -> ThresholdConfig:
        return ThresholdConfig(
            high_threshold=85,
            low_threshold=20,
            critical_threshold=5,
            hysteresis=3,
        )

    @pytest.fixture
    def state_machine(self, config: ThresholdConfig) -> ThresholdStateMachine:
        return ThresholdStateMachine(config=config)

    def test_initial_state(self, state_machine: ThresholdStateMachine) -> None:
        """Test initial state is NORMAL."""
        assert state_machine.current_state == ThresholdState.NORMAL
        assert state_machine.is_alarm_active is False

    def test_approaching_full(self, state_machine: ThresholdStateMachine) -> None:
        """Test APPROACHING_FULL state when charging near high threshold."""
        state = state_machine.update(83, True)
        assert state == ThresholdState.APPROACHING_FULL
        assert state_machine.is_alarm_active is False

    def test_full_alarm(self, state_machine: ThresholdStateMachine) -> None:
        """Test FULL_ALARM state when charging reaches high threshold."""
        state = state_machine.update(85, True)
        assert state == ThresholdState.FULL_ALARM
        assert state_machine.is_alarm_active is True

    def test_approaching_low(self, state_machine: ThresholdStateMachine) -> None:
        """Test APPROACHING_LOW state when discharging near low threshold."""
        state = state_machine.update(22, False)
        assert state == ThresholdState.APPROACHING_LOW
        assert state_machine.is_alarm_active is False

    def test_low_alarm(self, state_machine: ThresholdStateMachine) -> None:
        """Test LOW_ALARM state when discharging reaches low threshold."""
        state = state_machine.update(20, False)
        assert state == ThresholdState.LOW_ALARM
        assert state_machine.is_alarm_active is True

    def test_critical_low(self, state_machine: ThresholdStateMachine) -> None:
        """Test CRITICAL_LOW state when below critical threshold."""
        state = state_machine.update(4, False)
        assert state == ThresholdState.CRITICAL_LOW
        assert state_machine.is_alarm_active is True

    def test_hysteresis_full_alarm(self, state_machine: ThresholdStateMachine) -> None:
        """Test hysteresis prevents flapping for FULL_ALARM."""
        # Enter FULL_ALARM
        state = state_machine.update(85, True)
        assert state == ThresholdState.FULL_ALARM

        # Drop slightly below (still within hysteresis zone)
        state = state_machine.update(83, True)
        # Should stay in FULL_ALARM due to hysteresis
        assert state == ThresholdState.FULL_ALARM

        # Drop below hysteresis margin
        state = state_machine.update(81, True)
        assert state == ThresholdState.APPROACHING_FULL

    def test_hysteresis_low_alarm(self, state_machine: ThresholdStateMachine) -> None:
        """Test hysteresis prevents flapping for LOW_ALARM."""
        # Enter LOW_ALARM
        state = state_machine.update(20, False)
        assert state == ThresholdState.LOW_ALARM

        # Rise slightly above (still within hysteresis zone)
        state = state_machine.update(22, False)
        # Should stay in LOW_ALARM due to hysteresis
        assert state == ThresholdState.LOW_ALARM

        # Rise above hysteresis margin
        state = state_machine.update(24, False)
        assert state == ThresholdState.APPROACHING_LOW

    def test_critical_low_priority(self, state_machine: ThresholdStateMachine) -> None:
        """Test CRITICAL_LOW has highest priority."""
        # Enter FULL_ALARM
        state = state_machine.update(85, True)
        assert state == ThresholdState.FULL_ALARM

        # Critical low should override
        state = state_machine.update(4, True)
        assert state == ThresholdState.CRITICAL_LOW

    def test_state_change_callback(self, config: ThresholdConfig) -> None:
        """Test state change callback is called."""
        changes = []

        def on_change(old: ThresholdState, new: ThresholdState) -> None:
            changes.append((old, new))

        machine = ThresholdStateMachine(config=config, on_state_change=on_change)

        # Trigger a state change
        machine.update(85, True)

        assert len(changes) == 1
        assert changes[0][0] == ThresholdState.NORMAL
        assert changes[0][1] == ThresholdState.FULL_ALARM

    def test_normal_from_low_alarm_on_charge(self, state_machine: ThresholdStateMachine) -> None:
        """Test LOW_ALARM exits when charging begins."""
        # Enter LOW_ALARM
        state = state_machine.update(20, False)
        assert state == ThresholdState.LOW_ALARM

        # Start charging
        state = state_machine.update(21, True)
        # Should exit alarm state
        assert state == ThresholdState.APPROACHING_FULL
        assert state_machine.is_alarm_active is False

    def test_reset(self, state_machine: ThresholdStateMachine) -> None:
        """Test resetting the state machine."""
        # Enter FULL_ALARM
        state = state_machine.update(85, True)
        assert state == ThresholdState.FULL_ALARM

        # Reset
        state_machine.reset()
        assert state_machine.current_state == ThresholdState.NORMAL
        assert state_machine.is_alarm_active is False

    def test_get_state_info(self, state_machine: ThresholdStateMachine) -> None:
        """Test get_state_info returns correct data."""
        state_machine.update(85, True)
        info = state_machine.get_state_info()

        assert info["current_state"] == ThresholdState.FULL_ALARM.value
        assert info["is_alarm_active"] is True
        assert info["last_percent"] == 85
        assert info["last_charging"] is True
        assert info["config"]["high_threshold"] == 85