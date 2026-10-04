"use client";

import React from "react";
import { MdCalendarToday, MdCheck, MdKeyboardArrowDown } from "react-icons/md";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { GlassWrapper } from "./DatePickerWithRange";

export type QuickRangeKey = "15m" | "1h" | "6h" | "24h" | "7d" | "30d";

export interface QuickRangeOption {
  key: QuickRangeKey;
  label: string;
  amount: number;
  unit: "minutes" | "hours" | "days";
}

export interface AnalyticsTimeFilter {
  kind: "quick" | "custom";
  quickRangeKey?: QuickRangeKey;
  quickRangeLabel?: string;
  startAt: string;
  endAt: string;
  timezone: "UTC";
}

interface TimeRangeDropdownProps {
  value: AnalyticsTimeFilter;
  onQuickRangeSelect: (range: QuickRangeOption) => void;
  onCustomRangeApply: (startAt: string, endAt: string, timezone: "UTC") => void;
}

export const QUICK_RANGES: QuickRangeOption[] = [
  { key: "15m", label: "Last 15 minutes", amount: 15, unit: "minutes" },
  { key: "1h", label: "Last 1 hour", amount: 1, unit: "hours" },
  { key: "6h", label: "Last 6 hours", amount: 6, unit: "hours" },
  { key: "24h", label: "Last 24 hours", amount: 24, unit: "hours" },
  { key: "7d", label: "Last 7 days", amount: 7, unit: "days" },
  { key: "30d", label: "Last 30 days", amount: 30, unit: "days" },
];

const pad2 = (value: number): string => String(value).padStart(2, "0");

const toUtcInputValue = (date: Date): string => {
  return [
    date.getUTCFullYear(),
    "-",
    pad2(date.getUTCMonth() + 1),
    "-",
    pad2(date.getUTCDate()),
    "T",
    pad2(date.getUTCHours()),
    ":",
    pad2(date.getUTCMinutes()),
  ].join("");
};

const parseUtcInputToIso = (value: string): string | null => {
  const match = value.match(
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/,
  );
  if (!match) {
    return null;
  }

  const [, year, month, day, hour, minute] = match;
  const utcTimestamp = Date.UTC(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour),
    Number(minute),
    0,
    0,
  );
  const date = new Date(utcTimestamp);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
};

const formatUtcForTrigger = (date: Date): string => {
  return [
    pad2(date.getUTCMonth() + 1),
    "/",
    pad2(date.getUTCDate()),
    "/",
    date.getUTCFullYear(),
    ", ",
    pad2(date.getUTCHours()),
    ":",
    pad2(date.getUTCMinutes()),
  ].join("");
};

const toWallClockInputValue = (date: Date): string => {
  return [
    date.getFullYear(),
    "-",
    pad2(date.getMonth() + 1),
    "-",
    pad2(date.getDate()),
    "T",
    pad2(date.getHours()),
    ":",
    pad2(date.getMinutes()),
  ].join("");
};

const formatWallClockForField = (value: string): string => {
  const date = value ? new Date(value) : null;
  if (!date || Number.isNaN(date.getTime())) {
    return "Select date";
  }

  const hours24 = date.getHours();
  const period = hours24 >= 12 ? "PM" : "AM";
  const hours12 = ((hours24 + 11) % 12) + 1;

  return `${pad2(date.getMonth() + 1)}/${pad2(date.getDate())}/${date.getFullYear()}, ${pad2(hours12)}:${pad2(date.getMinutes())} ${period}`;
};

const toTimeInputValue = (value: string): string => {
  const date = value ? new Date(value) : null;
  if (!date || Number.isNaN(date.getTime())) {
    return "00:00";
  }
  return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
};

const formatLabelForTrigger = (value: AnalyticsTimeFilter): string => {
  if (value.kind === "quick" && value.quickRangeLabel) {
    return value.quickRangeLabel;
  }

  const startDate = new Date(value.startAt);
  const endDate = new Date(value.endAt);
  const sameDay =
    startDate.getUTCFullYear() === endDate.getUTCFullYear() &&
    startDate.getUTCMonth() === endDate.getUTCMonth() &&
    startDate.getUTCDate() === endDate.getUTCDate();

  if (sameDay) {
    return `${formatUtcForTrigger(startDate)} -> ${pad2(endDate.getUTCHours())}:${pad2(endDate.getUTCMinutes())} UTC`;
  }

  return `${formatUtcForTrigger(startDate)} -> ${formatUtcForTrigger(endDate)} UTC`;
};

export default function TimeRangeDropdown({
  value,
  onQuickRangeSelect,
  onCustomRangeApply,
}: TimeRangeDropdownProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [isStartCalendarOpen, setIsStartCalendarOpen] = React.useState(false);
  const [isEndCalendarOpen, setIsEndCalendarOpen] = React.useState(false);
  const [customStartInput, setCustomStartInput] = React.useState<string>(
    toUtcInputValue(new Date(value.startAt)),
  );
  const [customEndInput, setCustomEndInput] = React.useState<string>(
    toUtcInputValue(new Date(value.endAt)),
  );
  const [customError, setCustomError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setCustomStartInput(toUtcInputValue(new Date(value.startAt)));
    setCustomEndInput(toUtcInputValue(new Date(value.endAt)));
    setCustomError(null);
  }, [value.startAt, value.endAt]);

  const applyCustomRange = () => {
    if (!customStartInput || !customEndInput) {
      setCustomError("Select both start and end time.");
      return;
    }

    const startIso = parseUtcInputToIso(customStartInput);
    const endIso = parseUtcInputToIso(customEndInput);
    if (!startIso || !endIso) {
      setCustomError("Enter a valid date and time.");
      return;
    }

    const start = new Date(startIso);
    const end = new Date(endIso);
    if (start >= end) {
      setCustomError("Start time must be before end time.");
      return;
    }

    const now = new Date();
    if (start > now || end > now) {
      setCustomError("Select a time range that is not in the future.");
      return;
    }

    setCustomError(null);
    onCustomRangeApply(startIso, endIso, "UTC");
    setIsOpen(false);
  };

  const handleStartDaySelect = (day: Date | undefined) => {
    if (!day) {
      return;
    }
    const current = customStartInput ? new Date(customStartInput) : new Date();
    const next = new Date(
      day.getFullYear(),
      day.getMonth(),
      day.getDate(),
      current.getHours(),
      current.getMinutes(),
    );
    setCustomStartInput(toWallClockInputValue(next));
    setIsStartCalendarOpen(false);
  };

  const handleEndDaySelect = (day: Date | undefined) => {
    if (!day) {
      return;
    }
    const current = customEndInput ? new Date(customEndInput) : new Date();
    const next = new Date(
      day.getFullYear(),
      day.getMonth(),
      day.getDate(),
      current.getHours(),
      current.getMinutes(),
    );
    setCustomEndInput(toWallClockInputValue(next));
    setIsEndCalendarOpen(false);
  };

  const handleStartTimeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const [hours, minutes] = event.target.value.split(":").map(Number);
    if (Number.isNaN(hours) || Number.isNaN(minutes)) {
      return;
    }
    const current = customStartInput ? new Date(customStartInput) : new Date();
    const next = new Date(
      current.getFullYear(),
      current.getMonth(),
      current.getDate(),
      hours,
      minutes,
    );
    setCustomStartInput(toWallClockInputValue(next));
  };

  const handleEndTimeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const [hours, minutes] = event.target.value.split(":").map(Number);
    if (Number.isNaN(hours) || Number.isNaN(minutes)) {
      return;
    }
    const current = customEndInput ? new Date(customEndInput) : new Date();
    const next = new Date(
      current.getFullYear(),
      current.getMonth(),
      current.getDate(),
      hours,
      minutes,
    );
    setCustomEndInput(toWallClockInputValue(next));
  };

  return (
    <Popover
      open={isOpen}
      onOpenChange={(open) => {
        setIsOpen(open);
        if (!open) {
          setIsStartCalendarOpen(false);
          setIsEndCalendarOpen(false);
        }
      }}
    >
      <PopoverTrigger asChild>
        <button
          className="inline-flex h-9 min-w-44 items-center justify-between gap-2 rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 text-sm font-medium text-zinc-200 transition-colors hover:bg-white/[0.06] hover:text-white"
          aria-label="Select analytics time range"
        >
          <span className="truncate">{formatLabelForTrigger(value)}</span>
          <MdKeyboardArrowDown className="h-4 w-4 shrink-0 text-zinc-400" />
        </button>
      </PopoverTrigger>
      <PopoverContent
        align="end"
        className="w-[360px] rounded-xl border border-white/[0.08] bg-[#090c17] p-3 text-zinc-200 shadow-2xl"
      >
        <div className="space-y-3">
          <section className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
              Quick ranges
            </p>
            <div className="space-y-1">
              {QUICK_RANGES.map((range) => {
                const isSelected =
                  value.kind === "quick" && value.quickRangeKey === range.key;
                return (
                  <button
                    key={range.key}
                    type="button"
                    onClick={() => {
                      onQuickRangeSelect(range);
                      setIsOpen(false);
                    }}
                    className={`flex w-full items-center justify-between rounded-md px-2.5 py-2 text-left text-sm transition-colors ${
                      isSelected
                        ? "bg-sky-500/10 text-sky-300"
                        : "text-zinc-300 hover:bg-white/[0.05] hover:text-white"
                    }`}
                  >
                    <span>{range.label}</span>
                    {isSelected ? <MdCheck className="h-4 w-4" /> : null}
                  </button>
                );
              })}
            </div>
          </section>

          <section className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                Custom range
              </p>
              <span className="text-[11px] text-zinc-500 tracking-wide">
                mm/dd/yyyy
              </span>
            </div>
            <div className="space-y-3">
              <div className="space-y-1.5">
                <label className="block text-xs font-medium text-zinc-400">
                  Start date
                </label>
                <Popover
                  open={isStartCalendarOpen}
                  onOpenChange={setIsStartCalendarOpen}
                >
                  <PopoverTrigger asChild>
                    <button
                      type="button"
                      className="flex h-9 w-full items-center justify-between gap-2 rounded-md border border-white/[0.1] bg-[#0c1222] px-2 text-left text-xs text-zinc-200 outline-none transition-colors hover:border-white/[0.2] focus:border-sky-500/50"
                    >
                      <span>{formatWallClockForField(customStartInput)}</span>
                      <MdCalendarToday className="h-3.5 w-3.5 shrink-0 text-zinc-500" />
                    </button>
                  </PopoverTrigger>
                  <PopoverContent
                    align="start"
                    className="w-auto border-none bg-transparent p-0 shadow-none"
                  >
                    <GlassWrapper>
                      <Calendar
                        mode="single"
                        autoFocus
                        selected={
                          customStartInput ? new Date(customStartInput) : undefined
                        }
                        onSelect={handleStartDaySelect}
                        disabled={(day) => {
                          if (customEndInput && day > new Date(customEndInput)) {
                            return true;
                          }
                          if (day > new Date()) {
                            return true;
                          }
                          return false;
                        }}
                      />
                      <div className="mt-2 flex items-center justify-between border-t border-white/[0.08] pt-2">
                        <span className="text-xs text-zinc-400">Time</span>
                        <input
                          type="time"
                          value={toTimeInputValue(customStartInput)}
                          onChange={handleStartTimeChange}
                          className="h-8 rounded-md border border-white/[0.1] bg-[#0c1222] px-2 text-xs text-zinc-200 outline-none focus:border-sky-500/50"
                        />
                      </div>
                    </GlassWrapper>
                  </PopoverContent>
                </Popover>
              </div>
              <div className="space-y-1.5">
                <label className="block text-xs font-medium text-zinc-400">
                  End date
                </label>
                <Popover
                  open={isEndCalendarOpen}
                  onOpenChange={setIsEndCalendarOpen}
                >
                  <PopoverTrigger asChild>
                    <button
                      type="button"
                      className="flex h-9 w-full items-center justify-between gap-2 rounded-md border border-white/[0.1] bg-[#0c1222] px-2 text-left text-xs text-zinc-200 outline-none transition-colors hover:border-white/[0.2] focus:border-sky-500/50"
                    >
                      <span>{formatWallClockForField(customEndInput)}</span>
                      <MdCalendarToday className="h-3.5 w-3.5 shrink-0 text-zinc-500" />
                    </button>
                  </PopoverTrigger>
                  <PopoverContent
                    align="start"
                    className="w-auto border-none bg-transparent p-0 shadow-none"
                  >
                    <GlassWrapper>
                      <Calendar
                        mode="single"
                        autoFocus
                        selected={
                          customEndInput ? new Date(customEndInput) : undefined
                        }
                        onSelect={handleEndDaySelect}
                        disabled={(day) => {
                          if (customStartInput) {
                            const start = new Date(customStartInput);
                            const startOfStartDay = new Date(
                              start.getFullYear(),
                              start.getMonth(),
                              start.getDate(),
                            );
                            if (day < startOfStartDay) {
                              return true;
                            }
                          }
                          if (day > new Date()) {
                            return true;
                          }
                          return false;
                        }}
                      />
                      <div className="mt-2 flex items-center justify-between border-t border-white/[0.08] pt-2">
                        <span className="text-xs text-zinc-400">Time</span>
                        <input
                          type="time"
                          value={toTimeInputValue(customEndInput)}
                          onChange={handleEndTimeChange}
                          className="h-8 rounded-md border border-white/[0.1] bg-[#0c1222] px-2 text-xs text-zinc-200 outline-none focus:border-sky-500/50"
                        />
                      </div>
                    </GlassWrapper>
                  </PopoverContent>
                </Popover>
              </div>
            </div>
            <div className="mt-3 flex items-center justify-between gap-2 border-t border-white/[0.06] pt-2.5">
              <div className="min-h-4">
                <p className="text-xs text-zinc-500">Timezone: UTC</p>
                {customError ? (
                  <p className="text-xs text-rose-400">{customError}</p>
                ) : null}
              </div>
              <button
                type="button"
                onClick={applyCustomRange}
                className="inline-flex h-8 items-center justify-center rounded-md border border-sky-500/30 bg-sky-500/10 px-3 text-xs font-medium text-sky-300 transition-colors hover:bg-sky-500/20"
              >
                Apply
              </button>
            </div>
          </section>
        </div>
      </PopoverContent>
    </Popover>
  );
}
