# Chat scroll region

## Goal

Keep the application at the viewport height. The chat history is the only
vertically scrollable area; the workspace header and message composer remain
visible.

## Design

`ChatView` remains a three-row CSS grid: header, transcript, composer. The
chat panel gets a fixed viewport height and hidden overflow. The transcript
receives `min-height: 0` and `overflow-y: auto`, allowing long answers and old
messages to scroll inside its own region without expanding the page.

The existing responsive layout continues to use normal document flow on small
screens, where a fixed desktop-height panel would reduce usable space.

## Verification

Build the frontend, then send or load a long chat response. The browser body
must not scroll on desktop; only the transcript does, while the header and
composer remain visible.
