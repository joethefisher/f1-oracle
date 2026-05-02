# Workflow 06: Vercel Deployment

## Objective
Deploy the Next.js frontend to Vercel and keep it live.

## One-Time Setup (first deploy)

### 1. Import project to Vercel
1. Go to vercel.com → New Project
2. Import from GitHub: `joethefisher/f1-oracle`
3. Set **Root Directory** to `web`
4. Framework: Next.js (auto-detected)
5. Build command: `npm run build` (default)

### 2. Set environment variables in Vercel dashboard
Under Project Settings → Environment Variables, add:
```
NEXT_PUBLIC_SUPABASE_URL=https://goexgkwgaahdnolskmok.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<your publishable key from Supabase>
```

These are public keys (safe to expose in the browser). Do NOT add DATABASE_URL or ANTHROPIC_API_KEY to Vercel — those stay server-side in .env.

### 3. Deploy
Vercel auto-deploys on every push to `main`. The first deploy happens automatically after import.

## Ongoing
- Every `git push origin main` triggers a production deploy
- Preview deploys are created for pull requests (optional — repo is private)
- Logs: vercel.com → Project → Deployments → View logs

## Environment Variable Reference

| Variable | Where | Purpose |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Vercel + `.env.local` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Vercel + `.env.local` | Supabase public key (read-only) |
| `DATABASE_URL` | `.env` only | Direct Postgres connection (never Vercel) |
| `ANTHROPIC_API_KEY` | `.env` only | Post-mortem agent (never Vercel) |

## Troubleshooting
- **Build fails "Module not found"**: Check `web/package.json` has all dependencies installed
- **Supabase 401**: Verify `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` is set correctly in Vercel
- **Pages show "no data"**: Expected until models run and predictions are saved to DB
