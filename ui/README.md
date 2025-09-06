# Skyflo.ai UI

The command center for the Skyflo.ai platform. It provides an intuitive and powerful interface for interacting with the Sky AI agent that manage Cloud Native resources through natural language.

## How it fits with the backend

- Engine (FastAPI) exposes `/api/v1` with:
  - `POST /agent/chat` (SSE) for token/tool streaming
  - `POST /agent/approvals/{call_id}` (SSE) for approve/deny
  - `POST /agent/stop` for stopping a running turn
  - Auth, Team, and Conversations endpoints
- MCP server provides tool execution capabilities (kubectl, helm, argo) used by the Engine. The UI does not talk to MCP directly.

The UI communicates with the Engine in two ways:
- Client-side streaming via SSE to `NEXT_PUBLIC_API_URL/agent/*` using `ChatService`.
- Server-side API routes (Next.js App Router) under `src/app/api/*` act as a lightweight BFF/proxy to `API_URL/*`, forwarding cookies and Authorization headers.

## Project structure

```
ui/
├── src/
│   ├── app/                       # Next.js 14 App Router
│   │   ├── page.tsx               # Home -> Welcome flow
│   │   ├── login/page.tsx         # Auth UI
│   │   ├── chat/[id]/page.tsx     # Conversation view
│   │   ├── history/page.tsx       # History view
│   │   ├── settings/page.tsx      # Profile/Password
│   │   └── api/                   # BFF routes (proxy to Engine)
│   │       ├── conversation/      # list/create and by id CRUD
│   │       ├── auth/me            # current user
│   │       ├── auth/admin-check   # admin check
│   │       ├── profile            # update profile/password
│   │       └── team               # team management (admin)
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatInterface.tsx  # Orchestrates SSE session, tokens & tools
│   │   │   ├── ChatMessages.tsx   # Renders text/tool segments (Markdown)
│   │   │   ├── ChatInput.tsx      # Composer with stop+send
│   │   │   ├── ChatHeader.tsx     # Branding/header
│   │   │   ├── ChatSuggestions.tsx
│   │   │   └── ToolVisualization.tsx
│   │   ├── settings/              # Profile/Team components
│   │   ├── navbar/
│   │   └── ui/                    # Primitives (button, card, tooltip, etc.)
│   ├── lib/
│   │   ├── services/sseService.ts # Low-level SSE reader and event router
│   │   ├── api.ts                 # Cookie→Auth headers helper, create conversation
│   │   ├── auth.ts                # Login/register/logout/profile/password
│   │   ├── approvals.ts           # Approve/deny/stop helpers
│   │   ├── team.ts                # Team admin helpers
│   │   └── utils.ts
│   ├── store/
│   │   └── useAuthStore.ts        # Zustand-backed auth store
│   └── types/                     # Events, chat, auth types
└── next.config.mjs                # Next config (standalone output)
```

## Data flow (chat + tools)

1) User submits a prompt in `ChatInput`.
2) `ChatInterface` calls `ChatService.startStream()` which `fetch`es `NEXT_PUBLIC_API_URL/agent/chat` with `Accept: text/event-stream`.
3) SSE events from the Engine are parsed in `sseService.ts` and dispatched to `ChatInterface` callbacks:
   - `token`: incremental assistant text (Markdown rendered in `ChatMessages`)
   - `tools.pending`, `tool.executing`, `tool.result`, `tool.error`:
     shown inline via `ToolVisualization` segments
   - `tool.awaiting_approval`: UI prompts to approve/deny
   - `completed` / `workflow_complete`: finalization
4) Approvals use `ChatService.startApprovalStream(callId, approve, reason, conversationId)` which opens a second SSE stream to `/agent/approvals/{call_id}`.
5) A running turn can be stopped via `approvals.stopConversation(conversationId, runId)` → `POST /agent/stop`.

Conversations, history, profile, and team admin use server-side routes under `src/app/api/*` that forward to `API_URL` with the correct cookies/headers.

## Authentication

- Login uses Engine `POST /auth/jwt/login` and stores the `auth_token` as an HttpOnly cookie.
- Client requests to Engine include `Authorization: Bearer <auth_token>` built from cookies (`lib/api.ts`).
- `useAuthStore` persists minimal auth state in `localStorage` (Zustand), separate from HttpOnly auth cookie used on the server.

## Environment variables

Set both server and client base URLs for the Engine API:

```bash
# Server-side BFF → Engine (used by src/app/api/* and server actions)
API_URL=http://localhost:8080/api/v1

# Client-side SSE → Engine (used by ChatService in the browser)
NEXT_PUBLIC_API_URL=http://localhost:8080/api/v1

NODE_ENV=development
```

Notes:
- Ensure Engine CORS allows the UI origin (or place UI behind the provided Nginx proxy, see deployment assets).
- Default Engine port is 8080; MCP typically runs on 8888 (not used directly by the UI).

## Getting started (development)

```bash
cd ui
yarn install
yarn dev
# http://localhost:3000
```

## Production build

```bash
yarn build
yarn start
```

`next.config.mjs` outputs a standalone build suitable for containerization. See `deployment/ui/` for Nginx and container examples.

## Key components

- Chat
  - `ChatInterface.tsx`: state machine for streaming turns, approvals, stop
  - `ChatMessages.tsx`: renders Markdown and tool segments
  - `ChatInput.tsx`: input + stop control
  - `ToolVisualization.tsx`: compact view of tool execution results/errors
- Settings
  - Profile (name), password change via `/auth/me` and `/auth/users/me/password`
  - Team admin (members, invitations, roles) via `/team/*` (admin only)

## Server routes (BFF)

- `GET/POST /api/conversation` → Engine conversations list/create
- `GET/PATCH/DELETE /api/conversation/[id]` → per-conversation ops
- `GET /api/auth/me` and `GET /api/auth/admin-check`
- `PATCH/POST /api/profile` → profile update / password change
- `GET/POST/PATCH/DELETE /api/team` → members, roles, invitations (admin)

## Tech stack

| Component            | Technology            |
|----------------------|-----------------------|
| Framework            | Next.js 14            |
| Language             | TypeScript 5          |
| Styling              | Tailwind CSS          |
| State Management     | React + Zustand       |
| Streaming            | Server‑Sent Events    |
| Markdown             | react-markdown        |
| Animations           | framer-motion         |

## Troubleshooting

- Cannot connect to backend during chat: verify `NEXT_PUBLIC_API_URL` and Engine on `:8080`, CORS, and network. The UI surfaces detailed errors from `sseService.ts`.
- Approvals stream 404: ensure `POST /agent/approvals/{call_id}` exists on Engine and the `call_id` is correct.
- Auth issues: confirm `auth_token` cookie is present and forwarded; server routes build headers via `lib/api.ts`.

## Community and Support

- Website: https://skyflo.ai
- Discord: https://discord.gg/kCFNavMund
- X/Twitter: https://x.com/skyflo_ai
- GitHub Discussions: https://github.com/skyflo-ai/skyflo/discussions
