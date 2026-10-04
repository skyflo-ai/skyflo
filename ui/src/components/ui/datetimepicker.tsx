import React, { type ChangeEventHandler, useEffect, useState } from "react";

import { format, setHours, setMinutes } from "date-fns";
import { DayPicker } from "react-day-picker";

export function InputTime() {
  const [selected, setSelected] = useState<Date>();
  const [timeValue, setTimeValue] = useState<string>("00:00");

  // Keep the time input in sync when the selected date changes elsewhere.
  useEffect(() => {
    if (selected) {
      setTimeValue(format(selected, "HH:mm"));
    }
  }, [selected]);

  const handleTimeChange: ChangeEventHandler<HTMLInputElement> = (e) => {
    const time = e.target.value;
    if (!time) {
      return;
    }

    const [hours, minutes] = time.split(":").map((str) => parseInt(str, 10));
    const isValidTime =
      Number.isFinite(hours) &&
      Number.isFinite(minutes) &&
      hours >= 0 &&
      hours <= 23 &&
      minutes >= 0 &&
      minutes <= 59;
    if (!isValidTime) {
      return;
    }

    if (!selected) {
      // Defer composing a full Date until a day is picked.
      setTimeValue(time);
      return;
    }
    // Compose a new Date using the current day plus the chosen time.
    const newSelectedDate = setHours(setMinutes(selected, minutes), hours);
    setSelected(newSelectedDate);
    setTimeValue(time);
  };

  const handleDaySelect = (date: Date | undefined) => {
    if (!timeValue || !date) {
      setSelected(date);
      return;
    }
    const [hours, minutes] = timeValue
      .split(":")
      .map((str) => parseInt(str, 10));
    const newDate = new Date(
      date.getFullYear(),
      date.getMonth(),
      date.getDate(),
      hours,
      minutes,
    );
    setSelected(newDate);
  };

  return (
    <div className="absolute rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 bg-slate-700 w-80">
      <form style={{ marginBlockEnd: "1em" }}>
        <label>
          Set the time:{" "}
          <input className="bg-transparent border-b border-white/[0.1] p-1 text-sm focus:outline-none" type="time" value={timeValue} onChange={handleTimeChange} />
        </label>
      </form>
      <DayPicker
        mode="single"
        selected={selected}
        onSelect={handleDaySelect}
        
      />
    </div>
  );
}