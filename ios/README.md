# StaturdayRankings — iOS app (learning sandbox)

A minimal SwiftUI app that displays the live Top 25 from this project's API
(`GET /api/rankings`). It's a scratch space for learning Swift; design ideas
that feel good here can be backported to the web frontend.

The Swift source here is **not** an Xcode project on its own — Xcode generates
the `.xcodeproj`/build settings. Use one of the two flows below.

## First run

1. Xcode → **File ▸ New ▸ Project ▸ iOS ▸ App**.
   - Product Name: `StaturdayRankings`
   - Interface: **SwiftUI**, Language: **Swift**, Storage: **None**
2. In the generated project, replace the default `ContentView.swift` with the
   one in `StaturdayRankings/ContentView.swift`, and add `Models.swift`
   (drag it into the project navigator, or **File ▸ Add Files…**).
3. Press **⌘R**. You should see a scrollable Top 25 with name, conference,
   ELO, and record. Pull down to refresh.

After that first copy, keep editing the files here in the repo and paste/sync
into the Xcode project as you go (or point Xcode at these files directly via
**Add Files… ▸ uncheck "Copy items if needed"** so they stay version-tracked).

## Files

- `StaturdayRankings/Models.swift` — `Codable` structs mirroring the API's
  `RankingsResponse` / `RankingEntry` (see `src/api/schemas.py`). Field-name
  mapping (snake_case → camelCase) lives in the `CodingKeys` enums.
- `StaturdayRankings/ContentView.swift` — the list UI plus an async
  `URLSession` fetch. The API base URL is the `apiBase` constant at the top.

## Notes

- **API base URL** is `https://cfb.bdailey.com` in `ContentView.swift`. If the
  live domain differs, change that one constant.
- **HTTPS only.** Pointing `apiBase` at `http://localhost:...` will be blocked
  by App Transport Security until you add an Info.plist exception. The HTTPS
  production URL needs no configuration.
- The season/week label is shown via a bottom `.overlay` rather than
  `navigationSubtitle` so it runs on any iOS version.

## Ideas to extend (each a small Swift lesson)

- Tap a row → push a `TeamDetail` view (`NavigationLink`).
- `.searchable(text:)` to filter the list.
- A second tab hitting `/api/predictions` (`TabView` + a new model).
- A WidgetKit extension reusing `Models.swift` for a home-screen Top 25.
