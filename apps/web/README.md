# NightLedger Web Journal

This is the web view for the NightLedger journal timeline.

## Quick Start

To view the timeline locally, run:

```bash
npm start
```

Then open [http://localhost:3000](http://localhost:3000) (or the port shown in
your terminal).

## Note on Local Viewing

This application uses **JavaScript Modules** (`type="module"`), which means it
**cannot** be opened directly by double-clicking `index.html` (the `file://`
protocol). It must be served via a local web server.

## Demo Mode

By default, if no `runId` is provided in the URL, the app defaults to a **demo
mode** using mock data. You can specify a run ID via the query string:

- Demo: `http://localhost:3000/`
- Specific Run: `http://localhost:3000/?runId=your-run-id`
