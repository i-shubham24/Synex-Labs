# Synex Labs

Portfolio site for Synex Labs, a two person web studio (Shubham and Nitin).
Next.js 16 with React 19, Tailwind CSS 4 and Motion.

## Run it

```bash
npm install
npm run dev        # http://localhost:3000
npm run build      # production build
npm run start      # serve the build
npm run lint
npm run links      # check every project link still answers
```

## Where things live

- `src/data/projects.ts`: every project on the site, in display order. The main list is `projects`, the grid under it is `moreProjects`. Each one also gets its own page at `/work/<slug>` with its own share image.
- `src/data/content.ts`: services, numbers, process steps, team, FAQ.
- `src/lib/site.ts`: studio name, email, URL and nav.
- `public/work/<slug>/`: screenshots, `desktop-N.webp` and `mobile.webp`.

## Screenshots

`npm run shots` captures fresh screenshots of every project listed in `scripts/capture.mjs` (needs Chrome).
`npm run shots -- infini` captures only the slugs you name. It rewrites `src/data/shots.json`, clears the Next image cache and saves page text to `.shots/` (gitignored, never in `public/`).

## Environment

Copy `.env.example` to `.env.local`. `NEXT_PUBLIC_SITE_URL` sets the canonical URL for metadata, the sitemap and share images.

| Setting | What it turns on | Without it |
| --- | --- | --- |
| `RESEND_API_KEY`, `CONTACT_TO_EMAIL` | Contact briefs are emailed to the studio | The form opens the visitor's mail app with the brief filled in |
| `CONTACT_FROM_EMAIL` | Sender on a domain verified in Resend | `onboarding@resend.dev` (only delivers to the Resend account's own address) |
| `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN` | One contact rate limit shared by every server instance | A separate in-memory limit per instance |
| `GOOGLE_SITE_VERIFICATION` | Search Console ownership tag | No tag |

Page view analytics (Vercel Web Analytics, no cookies) switch on by themselves when the site is built on Vercel. Enable Web Analytics in the Vercel project settings.

## Checks

- `.github/workflows/ci.yml`: lint, typecheck and build on every push.
- `.github/workflows/links.yml`: every Monday, `npm run links` checks each project's live site and store pages. A failed run means a link on the site has gone dead.
