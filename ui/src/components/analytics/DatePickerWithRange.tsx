"use client"

import * as React from "react"
import { format } from "date-fns"
import { Calendar as CalendarIcon } from "lucide-react"
import { DateRange } from "react-day-picker"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"

interface DatePickerWithRangeProps extends React.HTMLAttributes<HTMLDivElement> {
    date: DateRange | undefined
    setDate: (date: DateRange | undefined) => void
}

export function DatePickerWithRange({
    className,
    date,
    setDate,
}: DatePickerWithRangeProps) {
    const [isStartOpen, setIsStartOpen] = React.useState(false)
    const [isEndOpen, setIsEndOpen] = React.useState(false)

    // Wraps content in the liquid glass effect structure
    const GlassWrapper = ({ children }: { children: React.ReactNode }) => (
        <div className="lg-wrapper">
            <div className="lg-effect" />
            <div className="lg-tint" />
            <div className="lg-shine" />
            <div className="relative z-10 p-2">
                {children}
            </div>
        </div>
    )

    return (
        <div className={cn("flex gap-2 max-sm:flex-col", className)}>
            {/* Start Date Picker */}
            <Popover open={isStartOpen} onOpenChange={setIsStartOpen}>
                <PopoverTrigger asChild>
                    <Button
                        id="start-date"
                        variant={"outline"}
                        className={cn(
                            "w-[140px] max-sm:w-full justify-start text-left font-medium border-white/10",
                            !date?.from && "text-muted-foreground"
                        )}
                    >
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {date?.from ? (
                            format(date.from, "LLL dd, y")
                        ) : (
                            <span>Start Date</span>
                        )}
                    </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0 border-none bg-transparent shadow-none" align="start">
                    <GlassWrapper>
                        <Calendar
                            initialFocus
                            mode="single"
                            selected={date?.from}
                            onSelect={(val) => {
                                // If picking a new start date that is after current end date, clear end date
                                if (val && date?.to && val > date.to) {
                                    setDate({ from: val, to: undefined })
                                } else {
                                    setDate({ from: val || undefined, to: date?.to })
                                }
                                setIsStartOpen(false)
                            }}
                            disabled={(day) => {
                                // Disable if after end date
                                if (date?.to && day > date.to) return true;
                                // Disable if future date
                                if (day > new Date()) return true;
                                return false;
                            }}
                        />
                    </GlassWrapper>
                </PopoverContent>
            </Popover>

            {/* End Date Picker */}
            <Popover open={isEndOpen} onOpenChange={setIsEndOpen}>
                <PopoverTrigger asChild>
                    <Button
                        id="end-date"
                        variant={"outline"}
                        className={cn(
                            "w-[140px] max-sm:w-full justify-start text-left font-medium border-white/10",
                            !date?.to && "text-muted-foreground"
                        )}
                        disabled={!date?.from}
                    >
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {date?.to ? (
                            format(date.to, "LLL dd, y")
                        ) : (
                            <span>End Date</span>
                        )}
                    </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0 border-none bg-transparent shadow-none" align="start">
                    <GlassWrapper>
                        <Calendar
                            initialFocus
                            mode="single"
                            selected={date?.to}
                            onSelect={(val) => {
                                setDate({ from: date?.from, to: val || undefined })
                                setIsEndOpen(false)
                            }}
                            disabled={(day) => {
                                // Disable if before start date
                                if (date?.from && day < date.from) return true;
                                // Disable if future date
                                if (day > new Date()) return true;
                                return false;
                            }}
                        />
                    </GlassWrapper>
                </PopoverContent>
            </Popover>
        </div>
    )
}
