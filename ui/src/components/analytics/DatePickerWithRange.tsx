"use client"

import * as React from "react"
import { format } from "date-fns"
import { DateRange } from "react-day-picker"
import { cn } from "@/lib/utils"
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DatePicker, DatePickerSlotProps } from '@mui/x-date-pickers/DatePicker';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { TextField } from "@mui/material";

interface DatePickerWithRangeProps {
    className?: string
    date: DateRange | undefined
    setDate: (date: DateRange | undefined) => void
}

const darkTheme = createTheme({
    palette: {
        mode: 'dark',
        primary: {
            main: '#3b82f6', // blue-500
        },
        background: {
            paper: '#0A1525', // card bg
            default: '#020817', // bg-background
        },
    },
    components: {
        MuiTextField: {
            // ... (keep MuiTextField styles if they were correct, but I'll re-include them to be safe)
            styleOverrides: {
                root: {
                    '& .MuiOutlinedInput-root': {
                        backgroundColor: 'rgba(255, 255, 255, 0.03)',
                        '& fieldset': {
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                        },
                        '&:hover fieldset': {
                            borderColor: 'rgba(255, 255, 255, 0.2)',
                        },
                        '&.Mui-focused fieldset': {
                            borderColor: '#3b82f6',
                        },
                    },
                    '& .MuiInputLabel-root': {
                        color: 'rgba(255, 255, 255, 0.7)',
                    },
                    '& .MuiInputBase-input': {
                        color: 'white',
                    },
                    '& .MuiSvgIcon-root': {
                        color: 'rgba(255, 255, 255, 0.7)',
                    }
                },
            },
        },
    },
});

const datePickerProps: DatePickerSlotProps<true> = {
    textField: {
        size: "small",
        sx: { width: 150 }
    },
    popper: {
        sx: {
            '& .MuiPaper-root': {
                border: '1px solid rgba(255, 255, 255, 0.1)',
                backgroundColor: '#3b82f61a',
                color: 'white',
            },
            '& .MuiPickersDay-root': {
                color: 'white',
                '&:hover': {
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                },
                '&.Mui-selected': {
                    backgroundColor: '#3b82f6',
                    '&:hover': {
                        backgroundColor: '#2563eb',
                    },
                },
            },
            '& .MuiPickersCalendarHeader-label': {
                color: 'white',
            },
            '& .MuiSvgIcon-root': {
                color: 'white',
            },
            '& .MuiDayCalendar-weekDayLabel': {
                color: 'rgba(255, 255, 255, 0.7)',
            }
        }
    }
}

export function DatePickerWithRange({
    className,
    date,
    setDate,
}: DatePickerWithRangeProps) {
    return (
        <ThemeProvider theme={darkTheme}>
            <LocalizationProvider dateAdapter={AdapterDateFns}>
                <div className={cn("grid gap-2 flex-row md:flex", className)}>
                    <DatePicker
                        label="Start Date"
                        value={date?.from || null}
                        onChange={(newValue) => {
                            setDate({ from: newValue || undefined, to: date?.to });
                        }}
                        maxDate={date?.to}
                        slotProps={datePickerProps}
                    />
                    <DatePicker
                        label="End Date"
                        value={date?.to || null}
                        onChange={(newValue) => {
                            setDate({ from: date?.from, to: newValue || undefined });
                        }}
                        minDate={date?.from}
                        slotProps={datePickerProps}
                    />
                </div>
            </LocalizationProvider>
        </ThemeProvider>
    )
}
