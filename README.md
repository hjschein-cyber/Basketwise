# Basketwise — produce price tracker

Mobile shopping-basket comparisons for **The Farmer**, **Rami Levy (Ramat Beit Shemesh)**, **Osher Ad (Beit Shemesh–Galil)** and a local fruit shop.

## Make it bookmarkable

GitHub repository: https://github.com/hjschein-cyber/Basketwise

1. Open **Settings → Pages** in this repository:
   https://github.com/hjschein-cyber/Basketwise/settings/pages
2. Under **Build and deployment**, select **Deploy from a branch**.
3. Select **main** and **/(root)**, then **Save**.
4. Once GitHub reports a successful deployment, open:
   https://hjschein-cyber.github.io/Basketwise/
5. On Android Chrome, use **⋮ → Add to Home screen**.

The HTML app works with its initial 56 Farmer products even before the scheduled price refresh runs. Data is stored only in your browser's localStorage. Export backups under **Settings & backup**; changing browser, clearing browser storage, or moving devices will not automatically preserve your manual entries.

## Weekly public price updates

The repository contains two GitHub Actions workflows at **Actions**:

- **Refresh The Farmer prices (weekly)** — every Monday; opens the publicly visible catalog in Chromium and attempts to parse public product cards.
- **Refresh Rami Levy and Osher Ad prices (weekly)** — every Monday; uses [israeli-prices](https://github.com/rxradar/israeli-prices) to read the official PriceFull files, verifies the two specific branch IDs, and conservatively matches identifiable, loose per-kg produce.

**These scrapers have not yet completed a verified live run.** Their behavior depends on upstream websites, official feed availability, and possible location restrictions. They refuse to overwrite existing valid data if the result looks incomplete; no prices from other branches or national averages are automatically substituted.

Run each workflow once manually from **Actions → select workflow → Run workflow**, then check the logs. To let a workflow commit its new JSON snapshots, repository **Settings → Actions → General → Workflow permissions** may need **Read and write permissions**. Weekly schedules are best-effort.

Published JSON files:

| File | Meaning |
|---|---|
| `farmer_prices.json` | Farmer catalog, currently seeded with 56 reference products dated November 18, 2026 |
| `supermarket_prices.json` | **Pending** until both local official price feeds verify successfully |
| `farmer_history.json` | Previous Farmer snapshots |
| `supermarket_history.json` | Previous official local-branch snapshots |

## Comparisons

Basketwise differentiates prices per kilogram, per item, and by package size. Farmer whole-package checkout estimates may differ from an exact-weight comparison. Missing prices are not treated as free. Published supermarket shelf prices can exclude promotional discounts, different grades, or varieties; always verify the physical shelf label.

Local store names and manual observations stay only on your device unless you export them. This public repository does **not** store your private shopping history.

## Public information sources

- https://thefarmer.co.il/
- https://url.publishedprices.co.il/
- https://github.com/rxradar/israeli-prices

This is an independent personal comparison tool, not an official retailer website.
