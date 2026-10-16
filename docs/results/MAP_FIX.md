# VayuSim basemap visibility fix

The user's Chrome screenshot shows OpenStreetMap's blocked-tile images. The
page's `Referrer-Policy: same-origin` caused cross-origin tile requests to omit
Referer. This violates the provider's [tile usage policy](https://operations.osmfoundation.org/policies/tiles/),
which requires web referrers and prohibits referrer-stripping policies.

MapLibre tile requests now explicitly use `strict-origin-when-cross-origin`,
limited to `https://tile.openstreetmap.org/`. Requests to that provider disclose
the origin, not the scenario URL/query. The site's general referrer policy,
attribution, browser caching and tile URL remain unchanged. No proxy, tile
prefetch or identity spoofing was added.

The initial Edge check did not reproduce Chrome's blocked images: its six tile
responses were already HTTP 200 despite an absent Referer. After the fix, all
six responses were HTTP 200 with `Referer: http://localhost:8000/`, and the
actual street map rendered. This confirms the corrected request behaviour;
it cannot guarantee that a provider lifts a separate network-level block.

A failed basemap source now hides that layer over a neutral background and
shows “Street map unavailable · plume and station locations remain visible.”
The georeferenced plume, stations and source controls remain usable. HTTP 403
fixtures passed at desktop and phone widths with no JavaScript errors or
horizontal overflow. Physics, stored fields, presets and example values are
unchanged. A hard refresh may be needed to discard a cached denial image.

- [After: rendered street map](map-fix-after.png).
- Simulated provider rejection: [desktop](map-fix-blocked-1440.png),
  [phone](map-fix-blocked-390.png).

Actual headers and fixture results are retained in `data/results/map-fix/`;
commands and output are in [VALIDATION.md](../VALIDATION.md), entries 026–030.
The subsequent [persistence verification](PHASE7_VERIFY.md) runs the full suite
against both changes before the local commit. No push is performed.
