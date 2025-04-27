# UI for Skyflo.ai

[![Next.js](https://img.shields.io/badge/Next.js-14%2B-black)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-3-blue)](https://tailwindcss.com/)


## Overview

This is the command center for the platform, providing an intuitive and powerful interface for interacting with the Sky AI agent that manage Cloud Native resources through natural language.

## Architecture

The UI implements a modern, component-based architecture built with Next.js and TypeScript:

### Application Structure

- **App Router** (`/src/app`): Next.js 14+ page routes and layouts
- **Components** (`/src/components`): Reusable UI elements and patterns
- **API Integration** (`/src/lib`): Service interfaces and API clients
- **State Management** (`/src/store`): Global state using Context API

### Key Components

- **ChatInterface** (`/src/components/ChatInterface.tsx`): 
  - Core conversational interface for interacting with AI agents
  - Real-time message streaming with WebSockets
  - Markdown rendering with syntax highlighting
  - Multi-agent workflow visualization

- **WebSocketProvider** (`/src/components/WebSocketProvider.tsx`):
  - Socket.io integration for real-time communication
  - Connection state management
  - Event handling for multi-agent updates
  - Conversation synchronization

- **AgentWorkflow** (`/src/components/AgentWorkflow.tsx`):
  - Visual representation of the Planner-Executor-Verifier workflow
  - Real-time execution stage visualization
  - Interactive step monitoring
  - Operation result display

## Installation

### Prerequisites

- Node.js 18+
- Yarn package manager
- Skyflo API Service (running locally or remotely)

### Development Setup

Clone the repository and install dependencies:

```bash
# Clone the repository
git clone https://github.com/skyflo-ai/skyflo.git
cd skyflo/ui

# Install dependencies
yarn install
```

Configure environment variables:

```bash
# Create .env file from example
cp .env.example .env

# Edit the .env file
NODE_ENV=development
```

Start the development server:

```bash
# Run in development mode
yarn dev
```

The UI will be available at http://localhost:3000.

```bash
# Or run with specific port
yarn dev -p 3001
```

### Production Build

Create and run an optimized production build:

```bash
# Build the application
yarn build

# Start the production server
yarn start
```

## Component Structure

```
ui/
├── src/
│   ├── app/              # Next.js 14+ pages and layouts
│   ├── components/       # Reusable UI components
│   │   ├── chat/        # Chat interface components
│   │   ├── workflow/    # Agent workflow visualizations
│   │   └── ui/          # Common UI elements
│   ├── lib/             # Utilities and API clients
│   │   ├── api/         # API integration layer
│   │   └── utils/       # Helper functions
│   ├── store/           # Global state management
│   └── styles/          # Global styles and Tailwind
├── public/              # Static assets
└── package.json         # Project configuration
```

## Development

### Design System

The UI follows a comprehensive design system:

- **Color Palette**:
  - Primary: #0F172A (Dark blue)
  - Secondary: #3B82F6 (Bright blue)
  - Accent: #10B981 (Green)
  - Alert: #EF4444 (Red)
  - Background: #F8FAFC (Light gray)
  - Text: #1E293B (Dark gray)

- **Typography**:
  - Text: Inter (Sans-serif)
  - Code: Fira Code (Monospace)

### Component Development

Follow these guidelines when creating components:

```tsx
// Example component following project standards
import React from 'react'
import { cn } from '@/lib/utils'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline'
  size?: 'sm' | 'md' | 'lg'
}

export function Button({
  variant = 'primary',
  size = 'md',
  className,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        // Base styles
        'rounded font-medium transition-colors focus:outline-none focus:ring-2',
        // Variant styles
        variant === 'primary' && 'bg-button-primary text-white hover:bg-button-hover',
        variant === 'secondary' && 'bg-dark-secondary text-white hover:bg-dark-hover',
        variant === 'outline' && 'border border-border text-gray-200 hover:bg-dark-hover',
        // Size styles
        size === 'sm' && 'px-3 py-1.5 text-sm',
        size === 'md' && 'px-4 py-2',
        size === 'lg' && 'px-5 py-2.5 text-lg',
        // Additional classes
        className
      )}
      {...props}
    />
  )
}
```

### State Management

The application uses a combination of:

- React Context for global state
- React hooks for component-specific state
- React Query for data fetching and caching
- Local storage for persistent preferences

## Tech Stack

| Component            | Technology                  |
|----------------------|-----------------------------|
| Framework            | Next.js 14+                 |
| Language             | TypeScript 5                |
| Styling              | Tailwind CSS                |
| State Management     | React Context               |
| WebSockets           | Socket.io                   |
| Markdown Rendering   | React Markdown              |
| Syntax Highlighting  | React Code Blocks           |
| Deployment           | Vercel / Docker             |

## Community and Support

- [Website](https://skyflo.ai)
- [Discord Community](https://discord.gg/kCFNavMund)
- [Twitter/X Updates](https://x.com/skyflo_ai)
- [GitHub Discussions](https://github.com/skyflo-ai/skyflo/discussions)
