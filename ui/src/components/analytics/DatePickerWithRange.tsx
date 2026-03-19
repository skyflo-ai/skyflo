"use client";

import * as React from "react";
import { format } from "date-fns";
import { MdCalendarToday } from "react-icons/md";
import { DateRange } from "react-day-picker";

import { cn } from "@/lib/utils";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

interface DatePickerWithRangeProps extends React.HTMLAttributes<HTMLDivElement> {
  date: DateRange | undefined;
  setDate: (date: DateRange | undefined) => void;
}

function GlassWrapper({ children }: { children: React.ReactNode }) {
  return (
    <div className="lg-wrapper">
      <div className="lg-effect" />
      <div className="lg-tint" />
      <div className="lg-shine" />
      <div className="relative z-10 p-2">{children}</div>
    </div>
  );
}

export function DatePickerWithRange({
  className,
  date,
  setDate,
}: DatePickerWithRangeProps) {
  const [isStartOpen, setIsStartOpen] = React.useState(false);
  const [isEndOpen, setIsEndOpen] = React.useState(false);

  return (
    <div
      className={cn(
        "flex shrink-0 items-center whitespace-nowrap rounded-lg border border-white/[0.06] bg-white/[0.03] p-0.5 gap-0.5",
        className,
      )}
    >
      <Popover open={isStartOpen} onOpenChange={setIsStartOpen}>
        <PopoverTrigger asChild>
          <button
            className={cn(
              "h-8 px-3 text-xs font-medium rounded-md transition-all duration-200 cursor-pointer inline-flex items-center gap-1.5",
              date?.from
                ? "text-zinc-300"
                : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04]",
            )}
          >
            <MdCalendarToday className="h-3 w-3 shrink-0" />
            {date?.from ? format(date.from, "LLL dd, y") : "Start Date"}
          </button>
        </PopoverTrigger>
        <PopoverContent
          className="w-auto p-0 border-none bg-transparent shadow-none"
          align="start"
        >
          <GlassWrapper>
            <Calendar
              autoFocus
              mode="single"
              selected={date?.from}
              onSelect={(val) => {
                if (!val) {
                  setDate({ from: undefined, to: undefined });
                } else if (date?.to && val > date.to) {
                  setDate({ from: val, to: undefined });
                } else {
                  setDate({ from: val, to: date?.to });
                }
                setIsStartOpen(false);
              }}
              disabled={(day) => {
                if (date?.to && day > date.to) return true;
                if (day > new Date()) return true;
                return false;
              }}
            />
          </GlassWrapper>
        </PopoverContent>
      </Popover>

      <div className="w-px h-4 bg-white/[0.08]" />

      <Popover open={isEndOpen} onOpenChange={setIsEndOpen}>
        <PopoverTrigger asChild>
          <button
            className={cn(
              "h-8 px-3 text-xs font-medium rounded-md transition-all duration-200 inline-flex items-center gap-1.5",
              !date?.from
                ? "text-zinc-600 cursor-not-allowed"
                : date?.to
                  ? "text-zinc-300 cursor-pointer"
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04] cursor-pointer",
            )}
            disabled={!date?.from}
          >
            <MdCalendarToday className="h-3 w-3 shrink-0" />
            {date?.to ? format(date.to, "LLL dd, y") : "End Date"}
          </button>
        </PopoverTrigger>
        <PopoverContent
          className="w-auto p-0 border-none bg-transparent shadow-none"
          align="start"
        >
          <GlassWrapper>
            <Calendar
              autoFocus
              mode="single"
              selected={date?.to}
              onSelect={(val) => {
                setDate({ from: date?.from, to: val || undefined });
                setIsEndOpen(false);
              }}
              disabled={(day) => {
                if (date?.from && day < date.from) return true;
                if (day > new Date()) return true;
                return false;
              }}
            />
          </GlassWrapper>
        </PopoverContent>
      </Popover>
    </div>
  );
}
