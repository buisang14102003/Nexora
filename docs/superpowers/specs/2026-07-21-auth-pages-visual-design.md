# Local RAG authentication pages visual design

## Goal

Apply a calm, minimal, ChatGPT-inspired visual system to the local Sign in and Sign up pages while retaining the existing native Chainlit login and FastAPI registration flow.

## Scope

- Style the Chainlit native sign-in page at port 8101 using CSS only.
- Restyle the FastAPI registration page at port 8100 using the same visual language.
- Provide visible, reciprocal links between Sign in and Sign up.
- Do not alter account APIs, JWTs, authentication callbacks, or chat UI.

## Layout

Both pages use a light, off-white canvas and a centered auth card. The card contains:

1. A compact circular RAG mark, drawn with CSS/text rather than an external asset.
2. `Welcome to Local RAG Workspace` heading.
3. One short sentence describing the local document workspace.
4. The existing email/password form and primary green action button.
5. A bottom link: `Don't have an account? Sign up` on sign-in, and `Already have an account? Sign in` on sign-up.

The page remains usable on narrow screens: card width is capped at 400px and horizontal padding reduces on mobile.

## Components and boundaries

### Chainlit sign-in presentation

- Configure Chainlit to load a local `public/auth.css` stylesheet.
- Use CSS selectors only; no JavaScript and no replacement login screen.
- Hide no native fields or buttons. CSS may adjust spacing, typography, card borders, and primary-button colors.
- Keep the existing login guidance to `http://127.0.0.1:8100/register` in the visible title/translation.

### FastAPI sign-up presentation

- Keep the `GET /register` and `POST /register` behavior unchanged.
- Replace only the inline registration HTML markup/style with semantic wrapper, mark, heading, subtitle, and shared class names.
- Serve `auth.css` from FastAPI's existing static/public mount or embed the matching small rule set when a shared mount is not present. There must be no external CDN assets.

## Visual tokens

- Background: `#f7f7f8`.
- Card: white with a subtle `#e5e7eb` border, 16px radius, soft shadow.
- Text: `#202123`; muted copy: `#6b7280`.
- Primary button: `#10a37f`, darkens on hover, white label.
- Font stack: system UI (`ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`).

## Error and accessibility behavior

- Existing registration errors remain inside the card above the form and use an accessible status region.
- Inputs retain native labels, `autocomplete` values, focus outlines, and password masking.
- Color is never the only error signal; error copy remains visible.
- The visual CSS must not expose credentials or change API error behavior.

## Verification

- Open `http://127.0.0.1:8101/login` and confirm the sign-in page has centered card, local RAG identity, visible registration path, native email/password controls, and login button.
- Open `http://127.0.0.1:8100/register` and confirm visual parity, local-only copy, and Sign in link.
- Submit an invalid registration and confirm its error stays visible inside the styled card.
- Verify responsive rendering with a narrow browser viewport and confirm login/register behavior is unchanged.
