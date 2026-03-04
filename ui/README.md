# Skyflo Command Center

The Command Center is Skyflo's operator interface. It renders agent execution in real time: tool calls, approval gates, audit history, and streaming output. All events stream from the [Engine](../engine) over SSE.

See the [architecture overview](https://skyflo.ai/docs/architecture) for full system context.

## How It Connects to the Backend

- Engine (FastAPI) exposes `/api/v1` with:
  - `POST /agent/chat` (SSE) for token/tool streaming
  - `POST /agent/approvals/{call_id}` (SSE) for approve/deny
  - `POST /agent/stop` for stopping a running turn
  - Auth, Team, Integrations, and Conversations endpoints
- MCP server provides tool execution capabilities (kubectl, helm, argo, jenkins) used by the Engine. The UI does not talk to MCP directly.

The UI communicates with the Engine in two ways:
- Client-side streaming via SSE to `NEXT_PUBLIC_API_URL/agent/*` using `ChatService`.
- Server-side API routes (Next.js App Router) under `src/app/api/*` act as a lightweight BFF/proxy to `API_URL/*`, forwarding cookies and Authorization headers.

## Data Flow (Chat + Tools)

1) User submits a prompt in `ChatInput`.
2) `ChatInterface` calls `ChatService.startStream()` which `fetch`es `NEXT_PUBLIC_API_URL/agent/chat` with `Accept: text/event-stream`.
3) SSE events from the Engine are parsed in `sseService.ts` and dispatched to `ChatInterface` callbacks:
   - `thinking`, `thinking.complete`: model reasoning tokens shown in collapsible `ThinkingBlock`
   - `token`: incremental assistant text (Markdown rendered in `ChatMessages`)
   - `tools.pending`, `tool.executing`, `tool.result`, `tool.error`: shown inline via `ToolVisualization` segments
   - `tool.awaiting_approval`: UI prompts to approve/deny
   - `token.usage`: LLM token metrics shown via `TokenUsageDisplay`
   - `ttft`: time-to-first-token latency
   - `completed` / `workflow_complete` / `workflow.error`: finalization
4) Approvals use `ChatService.startApprovalStream(callId, approve, reason, conversationId)` which opens a second SSE stream to `/agent/approvals/{call_id}`.
5) A running turn can be stopped via `approvals.stopConversation(conversationId, runId)` → `POST /agent/stop`.

Conversations, history, profile, and team admin use server-side routes under `src/app/api/*` that forward to `API_URL` with the correct cookies/headers.

## Authentication

- Login uses Engine `POST /auth/jwt/login` and stores `auth_token` and `refresh_token` as HttpOnly cookies.
- `AuthProvider` schedules automatic session refresh every 14 minutes via `POST /api/auth/refresh`, which rotates the refresh token and issues a new access token.
- Client requests to Engine include `Authorization: Bearer <auth_token>` built from cookies (`lib/api.ts`).
- Logout calls `POST /api/auth/logout` to revoke the refresh token and clear both cookies.
- `useAuthStore` persists minimal auth state in `localStorage` (Zustand), separate from the HttpOnly cookies used on the server.
- Token lifetimes are defined in `lib/auth/constants.ts` (access: 15 min, refresh: 7 days).

## Environment Variables

Defined in `.env.example`:

```bash
# Server-side BFF -> Engine (used by src/app/api/* routes)
API_URL=http://localhost:8080/api/v1

# Client-side SSE -> browser-routable Engine URL (used by ChatService in the browser)
NEXT_PUBLIC_API_URL=/api/v1
```

Notes:
- `NEXT_PUBLIC_API_URL` must be reachable from the browser. Use `/api/v1` behind the provided Nginx proxy, or a public URL such as `http://localhost:8080/api/v1` for local development without the proxy.
- Ensure Engine CORS allows the UI origin when `NEXT_PUBLIC_API_URL` points to a different origin.
- For SSE chat and approval streams, `ChatService` resolves auth headers server-side via `getAuthHeaders()`: the server reads the user's auth cookie, then returns a `Bearer` token in the `Authorization` header used for the browser `fetch` to `/agent/chat` and `/agent/approvals/*`.
- HttpOnly cookies alone are not enough for cross-origin SSE auth in this setup. If the UI talks to Engine across origins, make sure your proxy or auth middleware converts the session cookie into the `Authorization: Bearer ...` header for SSE requests, otherwise streaming requests will fail even if normal cookie-based login works.
- Default Engine port is 8080; MCP typically runs on 8888 (not used directly by the UI).

## Getting Started

```bash
cd ui
yarn install
yarn dev
# http://localhost:3000
```

## Development Commands

| Command | Description |
| ------- | ----------- |
| `yarn dev` | Start development server with hot reload |
| `yarn build` | Build for production |
| `yarn start` | Start production server |
| `yarn lint` | Run ESLint to check for code issues |

## Production Build

```bash
yarn build
yarn start
```

`next.config.mjs` outputs a standalone build suitable for containerization. See `deployment/ui/` for Nginx and container examples.

## Key Components

- Chat
  - `ChatInterface.tsx`: state machine for streaming turns, approvals, stop
  - `ChatMessages.tsx`: renders Markdown, thinking, and tool segments
  - `ChatInput.tsx`: input + stop control
  - `ThinkingBlock.tsx`: collapsible view of model reasoning with streaming animation and duration
  - `ToolVisualization.tsx`: compact view of tool execution results/errors
- Settings
  - Profile (name), password change via `/auth/me` and `/auth/users/me/password`
  - Team admin (members, invitations, roles) via `/team/*` (admin only)

## Server Routes (BFF)

- `GET/POST /api/conversation` → Engine conversations list/create
- `GET/PATCH/DELETE /api/conversation/[id]` → per-conversation ops
- `GET /api/auth/me` and `GET /api/auth/admin-check`
- `POST /api/auth/refresh` and `POST /api/auth/logout`
- `PATCH/POST /api/profile` → profile update / password change
- `GET/POST/PATCH/DELETE /api/team` → members, roles, invitations (admin)
- `GET/POST /api/integrations` and `PATCH/DELETE /api/integrations/[id]` → integrations admin (admin)

## Troubleshooting

- Cannot connect to backend during chat: verify `NEXT_PUBLIC_API_URL` and Engine on `:8080`, CORS, and network. The UI surfaces detailed errors from `sseService.ts`.
- Approvals stream 404: ensure `POST /agent/approvals/{call_id}` exists on Engine and the `call_id` is correct.
- Auth issues: confirm `auth_token` cookie is present and forwarded; server routes build headers via `lib/api.ts`.

## Tech Stack

| Component            | Technology            |
|----------------------|-----------------------|
| Framework            | Next.js 14            |
| Language             | TypeScript 5          |
| Styling              | Tailwind CSS          |
| UI Primitives        | Radix UI + shadcn/ui  |
| State Management     | React + Zustand       |
| Streaming            | Server-Sent Events    |
| Markdown             | react-markdown        |
| Animations           | framer-motion         |

## Community

- [Docs](https://skyflo.ai/docs)
- [Discord](https://discord.gg/kCFNavMund)
- [X](https://x.com/skyflo_ai)
- [LinkedIn](https://www.linkedin.com/company/skyflo)