# sautai React Frontend

A modern React SPA that replaces the Streamlit UI for **sautai**. It connects to the existing Django backend, preserves feature parity, and ships with a warm, community-focused brand theme.

## Features
- JWT auth (login/register), user profile & preferences
- AI chat
- Weekly meal plans with chef meal replacement/ordering
- Chef dashboard for offerings & orders
- Nutrition & health basics scaffolded (extend as needed)

## Quickstart

### Requirements
- Node.js >= 18 (recommended 20 LTS)
- npm >= 9 or pnpm/yarn
- A running Django backend (set `VITE_API_BASE` to its URL)

### Setup
```bash
npm install
npm run start
# open http://localhost:5173
```

### Config
Create a `.env` file in project root (optional):

```
VITE_API_BASE=http://localhost:8000
```

### Build
```bash
npm run build
npm run preview
```

## Notes
- API endpoints are aligned with the Django app used by the Streamlit UI (e.g., `/auth/api/token/`, `/auth/api/user_details/`, `/customer_dashboard/api/chat_with_gpt/`, `/meals/api/meal_plans/`, etc.).
- Adjust endpoints to match your backend if they differ.
- Components include clear comments and are structured for future expansion (native apps, streaming chat, etc.).

With warmth from the kitchen. 🍲
