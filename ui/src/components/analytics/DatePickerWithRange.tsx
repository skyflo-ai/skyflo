"use client"

import * as React from "react"
import { CalendarIcon } from "@radix-ui/react-icons"
import { format } from "date-fns"
import { DateRange } from "react-day-picker"
import { MdEditCalendar } from "react-icons/md"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"

interface DatePickerWithRangeProps {
    className?: string
    date: DateRange | undefined
    setDate: (date: DateRange | undefined) => void
}

export function DatePickerWithRange({
    className,
    date,
    setDate,
}: DatePickerWithRangeProps) {
    const [isOpen, setIsOpen] = React.useState(false)

    return (
        <div className={cn("grid gap-2 relative", className)}>
            <Button
                id="date"
                variant={"outline"}
                onClick={() => setIsOpen(!isOpen)}
                className={cn(
                    "w-[260px] justify-start text-left font-normal bg-dark-card border-white/10 text-white hover:bg-white/5 hover:text-white",
                    !date && "text-muted-foreground"
                )}
            >
                <MdEditCalendar className="mr-2 h-6 w-6" />
                {date?.from ? (
                    date.to ? (
                        <>
                            {format(date.from, "LLL dd, y")} -{" "}
                            {format(date.to, "LLL dd, y")}
                        </>
                    ) : (
                        format(date.from, "LLL dd, y")
                    )
                ) : (
                    <span>Pick a date</span>
                )}
            </Button>

            {isOpen && (
                <>
                    <div
                        className="fixed inset-0 z-40"
                        onClick={() => setIsOpen(false)}
                    />
                    <div className="absolute top-12 right-0 z-50 w-auto p-0 bg-[#0A1525]/50  border-[#1E2D45] rounded-xl border border-[#243147]/60 backdrop-blur-md shadow-lg shadow-blue-900/10">
                        <Calendar
                            initialFocus
                            mode="range"
                            defaultMonth={date?.from}
                            selected={date}
                            onSelect={(selectedDate) => {
                                setDate(selectedDate);
                                // Optionally close the popover after selection if it's a single date or range is complete
                                if (selectedDate?.from && selectedDate?.to) {
                                    setIsOpen(false);
                                }
                            }}
                            numberOfMonths={2}
                            className=" bg-[#0A1525]/50  border-[#1E2D45] rounded-xl border border-[#243147]/60 backdrop-blur-md shadow-lg shadow-blue-900/10 text-white"
                        />
                    </div>
                </>
            )}
        </div>
    )
}
