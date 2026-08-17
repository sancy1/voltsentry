"""
FILE: src/voltsentry/db/models.py
PATH: voltsentry/src/voltsentry/db/models.py
DESCRIPTION: SQLAlchemy ORM models for VoltSentry database
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, 
    Index, CheckConstraint, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class BatteryReading(Base):
    """
    Battery reading record.
    
    Stores individual battery readings at each poll interval.
    Used for historical analysis and health tracking.
    """
    __tablename__ = "battery_readings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    percent: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("percent >= 0 AND percent <= 100"),
        nullable=False,
    )
    is_charging: Mapped[bool] = mapped_column(Boolean, nullable=False)
    power_draw_watts: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default="estimated"
    )  # "os_report" | "estimated"

    __table_args__ = (
        Index("ix_battery_readings_timestamp_percent", "timestamp", "percent"),
    )

    def __repr__(self) -> str:
        return f"<BatteryReading(id={self.id}, percent={self.percent}, charging={self.is_charging})>"


class ChargeCycleEvent(Base):
    """
    Battery charge cycle tracking.
    
    Tracks cumulative charge cycles over time.
    Used for battery health calculations.
    """
    __tablename__ = "charge_cycle_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cycle_fraction: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    def __repr__(self) -> str:
        return f"<ChargeCycleEvent(id={self.id}, fraction={self.cycle_fraction})>"


class AlarmEvent(Base):
    """
    Alarm trigger records.
    
    Logs every alarm trigger for audit and analytics.
    Tracks user acknowledgment and snooze behavior.
    """
    __tablename__ = "alarm_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    alarm_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # "full_charge" | "low_battery" | "critical_low"
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    snoozed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    snooze_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_alarm_events_timestamp_type", "timestamp", "alarm_type"),
    )

    def __repr__(self) -> str:
        return f"<AlarmEvent(id={self.id}, type={self.alarm_type}, snoozed={self.snoozed})>"


class CalibrationRecord(Base):
    """
    Battery calibration session records.
    
    Tracks guided calibration sessions.
    Stores the resulting health score after calibration.
    """
    __tablename__ = "calibration_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    result_health_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    state: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="idle",
    )  # "idle" | "awaiting_full_charge" | "awaiting_full_discharge" | "recalculating" | "complete" | "aborted"

    def __repr__(self) -> str:
        return f"<CalibrationRecord(id={self.id}, state={self.state})>"


class AutomationHookLog(Base):
    """
    Automation hook invocation logs.
    
    Logs every webhook and script execution.
    Used for monitoring automation reliability.
    """
    __tablename__ = "automation_hook_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    hook_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # "webhook" | "script"
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_automation_hook_log_timestamp_type", "timestamp", "hook_type"),
    )

    def __repr__(self) -> str:
        return f"<AutomationHookLog(id={self.id}, type={self.hook_type}, success={self.success})>"
    