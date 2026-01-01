"use client"

import * as React from "react"
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DateCalendar } from '@mui/x-date-pickers/DateCalendar';
import { cn } from "@/lib/utils"
import { createTheme, ThemeProvider } from "@mui/material/styles";

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#3b82f6',
    },
    background: {
      paper: 'transparent',
      default: 'transparent',
    },
    text: {
      primary: '#ffffff',
      secondary: 'rgba(255, 255, 255, 0.7)',
    }
  },
  components: {
    MuiSvgIcon: {
      styleOverrides: {
        root: {
          color: '#ffffff',
        }
      }
    }
  }
});

function Calendar({
  className,
  ...props
}: React.ComponentProps<typeof DateCalendar> & { className?: string }) {
  return (
    <ThemeProvider theme={darkTheme}>
      <LocalizationProvider dateAdapter={AdapterDateFns}>
        <div className={cn("p-3", className)}>
          <DateCalendar
            {...props}
            slotProps={{
              day: {
                sx: {
                  color: '#ffffff',
                  '&.Mui-selected': {
                    backgroundColor: '#3b82f6 !important',
                  },
                  '&:hover': {
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                  }
                }
              },
              calendarHeader: {
                sx: {
                  '& .MuiPickersCalendarHeader-label': {
                    color: '#ffffff',
                  },
                  '& .MuiPickersCalendarHeader-switchViewIcon': {
                    color: '#ffffff',
                  }
                }
              }
            }}
            sx={{
              '& .MuiDayCalendar-weekDayLabel': {
                color: 'rgba(255, 255, 255, 0.7)',
              }
            }}
          />
        </div>
      </LocalizationProvider>
    </ThemeProvider>
  )
}

export { Calendar }
