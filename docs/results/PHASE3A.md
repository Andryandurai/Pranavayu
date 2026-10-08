# Phase 3A: actual data audit and analysis

Run **2**, recorded **2026-10-08T21:17:58.210107+05:30** (Asia/Kolkata). Data window 2015-01-01 to 2026-10-07. Results come from this run; the original pre-correction audit is retained from run 1.

## Flag audit

The headline flag rate included missing hours, not just invalid finite concentrations. The missing rule stays: at least three valid distinct quarters are required. Repeated zero alone cannot distinguish a reporting/detection floor from a frozen instrument, so zero flatlines are no longer automatically stuck. Equal hourly means are no longer marked stuck when their cached source quarters varied. Positive six-hour flatlines remain a conservative diagnostic, including rounded values; the available metadata does not establish instrument malfunction. PM2.5/PM10 comparisons are at the same station/hour in canonical µg/m³ and require both values. They remain diagnostic, not proof of calibration failure; separate instruments can disagree. Outlier thresholds stay 1000/2000 µg/m³ and keep measurements. No live negative/outlier example exists in this snapshot; their behavior is tested with synthetic cases.

| Source | Flag | Before | After | Before % | After % |
| --- | --- | --- | --- | --- | --- |
| cpcb-ccr | missing | 0 | 0 | 0.00 | 0.00 |
| cpcb-ccr | negative | 0 | 0 | 0.00 | 0.00 |
| cpcb-ccr | stuck | 7421 | 7421 | 0.50 | 0.50 |
| cpcb-ccr | pm25_gt_pm10 | 0 | 0 | 0.00 | 0.00 |
| cpcb-ccr | outlier | 0 | 0 | 0.00 | 0.00 |
| opencity | missing | 2950728 | 2950728 | 19.95 | 19.95 |
| opencity | negative | 0 | 0 | 0.00 | 0.00 |
| opencity | stuck | 104660 | 92162 | 0.71 | 0.62 |
| opencity | pm25_gt_pm10 | 1760 | 1760 | 0.01 | 0.01 |
| opencity | outlier | 0 | 0 | 0.00 | 0.00 |

Initial correction changed **12,498** flags in run **1**; this run changed **0**. This run inspected **104,660** quarter-backed candidates, **129** with varying quarters. The order-independent hash of every measurement/key/run link remained identical: `{'rows': 16266240, 'order_independent_record_hash': 695864490642684660}`. No value or raw_value was rewritten. Full breakdown by source, flag, pollutant, station and year is in flags_before.csv / flags_after.csv (this run); the initial baseline is in flag_audit.json; the evidence CSV preserves input paths and SHA256.

Real input examples: Peenya NO2 at 17.0 and NH3 at 12.53 on 2025-12-31 stayed flat in their original quarters while other variables changed. Velachery PM2.5 remained 7.73 while PM10 varied widely. These support retaining positive flatline screening. Sewri on 2025-12-14 23:15 UTC reports PM2.5 151.29 versus PM10 104.53, while adjacent quarters and other columns jump markedly; the inversion flag is a useful source-data warning, not something to repair by inventing values. Some inversions are tiny: the initial audit counted 581 of 1,760 within 5 µg/m³ and 482 within 10%; excluding them is conservative.

## Station and population decisions

| CPCB ID | Excluded station | Reason |
| --- | --- | --- |
| site_5405 | Alandi, Pune - IITM | Primary registry GPS unavailable; contributed coordinates unverified. |
| site_293 | Alandur Bus Depot, Chennai - CPCB | Primary registry GPS unavailable; contributed coordinates unverified. |
| site_5618 | Gandhi Nagar_Ennore, Chennai - TNPCB | Primary registry GPS unavailable; contributed coordinates unverified. |
| site_292 | Karve Road, Pune - MPCB | Primary registry GPS unavailable; contributed coordinates unverified. |
| site_5767 | Savitribai Phule Pune University, Pune - MPCB | Primary registry GPS unavailable; contributed coordinates unverified. |

These stations are excluded from city and spatial aggregation pending official GPS verification.

Default WorldPop: **2025**, `worldpop/ind_pop_2025_CN_100m_R2025A_v1.tif`, 778,106,191 bytes, SHA256 `f5717c622d79052d4aacf0f67365165575855ba8059375b5d87ea655ed26fa53`. This is a constrained R2025A v1 alpha modelled population estimate, not a census. The 2030 projection remains registered and is not default. No exposure calculation was performed. [Provider catalogue](https://hub.worldpop.org/geodata/summary?id=73807).

## Analysis-ready coverage

Materialised tables contain **1,228,198** city/pollutant/hour means. Only quality_flag=ok and non-excluded stations contribute, with station count per hour. Bins use IST calendar hours; ERA5 joins at the UTC timestamp of each local-hour midpoint (30 minutes after its start), without interpolation. Preserve original warehouse timestamps. OpenCity's explicit +0000 convention still needs independent verification before fine-scale cross-provider time comparisons. Daily means need 18 hours; monthly means need 75% of calendar days. A city-year is eligible only with at least 75% valid hours and 75% valid days. **52** PM2.5 city-years meet this stronger analysis rule.

| City | Year | Hours | Valid days | Calendar days | Valid months |
| --- | --- | --- | --- | --- | --- |
| ahmedabad | 2018 | 8158 | 322 | 365 | 11 |
| ahmedabad | 2019 | 8148 | 333 | 365 | 12 |
| bengaluru | 2015 | 6838 | 283 | 365 | 9 |
| bengaluru | 2016 | 7921 | 317 | 366 | 9 |
| bengaluru | 2017 | 8302 | 339 | 365 | 11 |
| bengaluru | 2018 | 8166 | 339 | 365 | 11 |
| bengaluru | 2019 | 8759 | 365 | 365 | 12 |
| bengaluru | 2024 | 8779 | 366 | 366 | 12 |
| bengaluru | 2025 | 8760 | 365 | 365 | 12 |
| chennai | 2016 | 8017 | 332 | 366 | 10 |
| chennai | 2017 | 8580 | 355 | 365 | 12 |
| chennai | 2018 | 8756 | 365 | 365 | 12 |
| chennai | 2019 | 8754 | 365 | 365 | 12 |
| chennai | 2024 | 8779 | 366 | 366 | 12 |
| chennai | 2025 | 8760 | 365 | 365 | 12 |
| delhi | 2015 | 8534 | 353 | 365 | 12 |
| delhi | 2016 | 8760 | 364 | 366 | 12 |
| delhi | 2017 | 8760 | 365 | 365 | 12 |
| delhi | 2018 | 8760 | 365 | 365 | 12 |
| delhi | 2019 | 8760 | 365 | 365 | 12 |
| delhi | 2024 | 8779 | 366 | 366 | 12 |
| delhi | 2025 | 8760 | 365 | 365 | 12 |
| hyderabad | 2016 | 8130 | 328 | 366 | 11 |
| hyderabad | 2017 | 8704 | 362 | 365 | 12 |
| hyderabad | 2018 | 8756 | 365 | 365 | 12 |
| hyderabad | 2019 | 8760 | 365 | 365 | 12 |
| hyderabad | 2024 | 8779 | 366 | 366 | 12 |
| hyderabad | 2025 | 8760 | 365 | 365 | 12 |
| jaipur | 2018 | 8752 | 365 | 365 | 12 |
| jaipur | 2019 | 8756 | 365 | 365 | 12 |
| kanpur | 2016 | 7743 | 304 | 366 | 10 |
| kanpur | 2017 | 7608 | 301 | 365 | 10 |
| kanpur | 2018 | 8423 | 345 | 365 | 11 |
| kanpur | 2019 | 8232 | 337 | 365 | 11 |
| kolkata | 2019 | 8756 | 365 | 365 | 12 |
| kolkata | 2024 | 8779 | 366 | 366 | 12 |
| kolkata | 2025 | 8760 | 365 | 365 | 12 |
| lucknow | 2015 | 6840 | 283 | 365 | 9 |
| lucknow | 2016 | 8077 | 326 | 366 | 9 |
| lucknow | 2017 | 7854 | 327 | 365 | 11 |
| lucknow | 2018 | 8478 | 350 | 365 | 12 |
| lucknow | 2019 | 8756 | 365 | 365 | 12 |
| mumbai | 2015 | 8649 | 360 | 365 | 12 |
| mumbai | 2016 | 8342 | 344 | 366 | 11 |
| mumbai | 2017 | 7672 | 312 | 365 | 11 |
| mumbai | 2019 | 8663 | 363 | 365 | 12 |
| mumbai | 2024 | 8779 | 366 | 366 | 12 |
| mumbai | 2025 | 8760 | 365 | 365 | 12 |
| patna | 2018 | 8462 | 351 | 365 | 12 |
| patna | 2019 | 8469 | 348 | 365 | 12 |
| pune | 2024 | 8779 | 366 | 366 | 12 |
| pune | 2025 | 8760 | 365 | 365 | 12 |

All pollutants/years, including zero coverage, are in analysis_coverage.csv. Calendar gaps describe missingness and are never used as model observations.

## Descriptive results

Annual means average valid daily means, with within-year ranks among eligible cities only. Exceedance counts use strict >60 µg/m³ (NAAQS) and >15 µg/m³ (WHO 2021).

| City | Year | Annual PM2.5 | Valid days | >60 days | >15 days | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| delhi | 2015 | 117.72 | 353 | 290 | 353 | 1 |
| lucknow | 2015 | 98.45 | 283 | 119 | 283 | 2 |
| mumbai | 2015 | 50.86 | 360 | 83 | 360 | 3 |
| bengaluru | 2015 | 33.62 | 283 | 26 | 249 | 4 |
| kanpur | 2016 | 141.32 | 304 | 221 | 304 | 1 |
| delhi | 2016 | 135.98 | 364 | 304 | 364 | 2 |
| lucknow | 2016 | 131.06 | 326 | 256 | 326 | 3 |
| chennai | 2016 | 53.29 | 332 | 126 | 331 | 4 |
| hyderabad | 2016 | 50.09 | 328 | 115 | 289 | 5 |
| bengaluru | 2016 | 46.33 | 317 | 74 | 303 | 6 |
| mumbai | 2016 | 38.62 | 344 | 59 | 306 | 7 |
| kanpur | 2017 | 145.04 | 301 | 222 | 301 | 1 |
| delhi | 2017 | 111.23 | 365 | 252 | 364 | 2 |
| lucknow | 2017 | 110.92 | 327 | 226 | 326 | 3 |
| chennai | 2017 | 48.47 | 355 | 85 | 350 | 4 |
| hyderabad | 2017 | 47.45 | 362 | 134 | 338 | 5 |
| mumbai | 2017 | 43.35 | 312 | 78 | 281 | 6 |
| bengaluru | 2017 | 32.64 | 339 | 25 | 305 | 7 |
| lucknow | 2018 | 124.58 | 350 | 270 | 348 | 1 |
| patna | 2018 | 117.86 | 351 | 267 | 351 | 2 |
| delhi | 2018 | 115.25 | 365 | 265 | 365 | 3 |
| kanpur | 2018 | 104.48 | 345 | 207 | 345 | 4 |
| ahmedabad | 2018 | 74.12 | 322 | 191 | 322 | 5 |
| jaipur | 2018 | 61.23 | 365 | 176 | 365 | 6 |
| chennai | 2018 | 51.02 | 365 | 108 | 365 | 7 |
| hyderabad | 2018 | 43.13 | 365 | 85 | 344 | 8 |
| bengaluru | 2018 | 34.65 | 339 | 28 | 327 | 9 |
| delhi | 2019 | 108.75 | 365 | 245 | 363 | 1 |
| patna | 2019 | 105.77 | 348 | 182 | 348 | 2 |
| lucknow | 2019 | 105.44 | 365 | 268 | 364 | 3 |
| kanpur | 2019 | 96.68 | 337 | 189 | 322 | 4 |
| kolkata | 2019 | 68.30 | 365 | 153 | 340 | 5 |
| ahmedabad | 2019 | 61.53 | 333 | 144 | 333 | 6 |
| jaipur | 2019 | 48.91 | 365 | 79 | 364 | 7 |
| chennai | 2019 | 43.02 | 365 | 57 | 353 | 8 |
| hyderabad | 2019 | 41.55 | 365 | 83 | 324 | 9 |
| bengaluru | 2019 | 35.27 | 365 | 26 | 342 | 10 |
| mumbai | 2019 | 34.82 | 363 | 75 | 254 | 11 |
| delhi | 2024 | 103.98 | 366 | 240 | 363 | 1 |
| kolkata | 2024 | 44.71 | 366 | 106 | 321 | 2 |
| pune | 2024 | 36.66 | 366 | 48 | 325 | 3 |
| mumbai | 2024 | 34.09 | 366 | 45 | 274 | 4 |
| bengaluru | 2024 | 32.27 | 366 | 9 | 350 | 5 |
| hyderabad | 2024 | 31.52 | 366 | 0 | 366 | 6 |
| chennai | 2024 | 24.31 | 366 | 6 | 272 | 7 |
| delhi | 2025 | 96.62 | 365 | 204 | 363 | 1 |
| kolkata | 2025 | 45.16 | 365 | 106 | 349 | 2 |
| pune | 2025 | 41.39 | 365 | 94 | 317 | 3 |
| hyderabad | 2025 | 35.02 | 365 | 0 | 365 | 4 |
| mumbai | 2025 | 34.32 | 365 | 39 | 347 | 5 |
| chennai | 2025 | 30.80 | 365 | 24 | 345 | 6 |
| bengaluru | 2025 | 29.39 | 365 | 2 | 360 | 7 |

Monthly climatology, seasonal diurnal profiles, weekday/weekend contrasts and winter-smog means with their contributing counts are stored in CSV and CityMetric. Winter-smog is Oct 15–Jan 31; the within-calendar-year contrast comprises Jan 1–31 and Oct 15–Dec 31.

| City | Year | Weekday PM2.5 | Weekdays | Weekend PM2.5 | Weekend days | Weekend − weekday |
| --- | --- | --- | --- | --- | --- | --- |
| ahmedabad | 2018 | 75.16 | 237 | 71.23 | 85 | -3.94 |
| ahmedabad | 2019 | 63.24 | 236 | 57.37 | 97 | -5.87 |
| bengaluru | 2015 | 33.57 | 202 | 33.73 | 81 | 0.16 |
| bengaluru | 2016 | 46.44 | 227 | 46.03 | 90 | -0.41 |
| bengaluru | 2017 | 33.62 | 239 | 30.31 | 100 | -3.31 |
| bengaluru | 2018 | 35.07 | 243 | 33.59 | 96 | -1.49 |
| bengaluru | 2019 | 35.63 | 261 | 34.36 | 104 | -1.26 |
| bengaluru | 2024 | 32.15 | 262 | 32.58 | 104 | 0.43 |
| bengaluru | 2025 | 29.31 | 261 | 29.57 | 104 | 0.26 |
| chennai | 2016 | 52.88 | 239 | 54.36 | 93 | 1.48 |
| chennai | 2017 | 48.31 | 254 | 48.88 | 101 | 0.57 |
| chennai | 2018 | 50.37 | 261 | 52.65 | 104 | 2.28 |
| chennai | 2019 | 44.26 | 261 | 39.91 | 104 | -4.35 |
| chennai | 2024 | 24.54 | 262 | 23.74 | 104 | -0.79 |
| chennai | 2025 | 30.95 | 261 | 30.41 | 104 | -0.54 |
| delhi | 2015 | 117.49 | 253 | 118.32 | 100 | 0.83 |
| delhi | 2016 | 134.68 | 261 | 139.29 | 103 | 4.62 |
| delhi | 2017 | 110.67 | 260 | 112.62 | 105 | 1.95 |
| delhi | 2018 | 117.12 | 261 | 110.54 | 104 | -6.58 |
| delhi | 2019 | 110.09 | 261 | 105.42 | 104 | -4.67 |
| delhi | 2024 | 104.24 | 262 | 103.33 | 104 | -0.91 |
| delhi | 2025 | 96.13 | 261 | 97.85 | 104 | 1.72 |
| hyderabad | 2016 | 51.43 | 239 | 46.49 | 89 | -4.94 |
| hyderabad | 2017 | 47.40 | 258 | 47.58 | 104 | 0.18 |
| hyderabad | 2018 | 43.05 | 261 | 43.34 | 104 | 0.28 |
| hyderabad | 2019 | 41.88 | 261 | 40.73 | 104 | -1.15 |
| hyderabad | 2024 | 31.56 | 262 | 31.42 | 104 | -0.14 |
| hyderabad | 2025 | 34.89 | 261 | 35.35 | 104 | 0.46 |
| jaipur | 2018 | 62.08 | 261 | 59.10 | 104 | -2.98 |
| jaipur | 2019 | 49.67 | 261 | 47.00 | 104 | -2.68 |
| kanpur | 2016 | 139.53 | 221 | 146.10 | 83 | 6.57 |
| kanpur | 2017 | 145.92 | 217 | 142.78 | 84 | -3.14 |
| kanpur | 2018 | 103.72 | 246 | 106.36 | 99 | 2.63 |
| kanpur | 2019 | 98.27 | 241 | 92.69 | 96 | -5.58 |
| kolkata | 2019 | 68.55 | 261 | 67.67 | 104 | -0.88 |
| kolkata | 2024 | 44.85 | 262 | 44.37 | 104 | -0.48 |
| kolkata | 2025 | 45.08 | 261 | 45.37 | 104 | 0.29 |
| lucknow | 2015 | 96.09 | 204 | 104.56 | 79 | 8.47 |
| lucknow | 2016 | 129.34 | 231 | 135.23 | 95 | 5.88 |
| lucknow | 2017 | 110.99 | 233 | 110.74 | 94 | -0.25 |
| lucknow | 2018 | 125.80 | 251 | 121.51 | 99 | -4.29 |
| lucknow | 2019 | 107.49 | 261 | 100.31 | 104 | -7.18 |
| mumbai | 2015 | 51.24 | 256 | 49.92 | 104 | -1.32 |
| mumbai | 2016 | 39.11 | 247 | 37.36 | 97 | -1.75 |
| mumbai | 2017 | 44.67 | 225 | 39.94 | 87 | -4.73 |
| mumbai | 2019 | 34.67 | 259 | 35.20 | 104 | 0.54 |
| mumbai | 2024 | 34.00 | 262 | 34.32 | 104 | 0.32 |
| mumbai | 2025 | 34.56 | 261 | 33.71 | 104 | -0.85 |
| patna | 2018 | 119.40 | 250 | 114.04 | 101 | -5.36 |
| patna | 2019 | 108.11 | 249 | 99.89 | 99 | -8.22 |
| pune | 2024 | 36.65 | 262 | 36.67 | 104 | 0.02 |
| pune | 2025 | 41.49 | 261 | 41.15 | 104 | -0.34 |

| City | Year | Winter PM2.5 | Winter days | Rest PM2.5 | Rest days |
| --- | --- | --- | --- | --- | --- |
| ahmedabad | 2018 | 95.69 | 102 | 64.12 | 220 |
| ahmedabad | 2019 | 71.46 | 103 | 57.08 | 230 |
| bengaluru | 2015 | 41.33 | 76 | 30.79 | 207 |
| bengaluru | 2016 | 53.27 | 109 | 42.68 | 208 |
| bengaluru | 2017 | 40.98 | 92 | 29.54 | 247 |
| bengaluru | 2018 | 45.84 | 108 | 29.42 | 231 |
| bengaluru | 2019 | 40.22 | 109 | 33.16 | 256 |
| bengaluru | 2024 | 38.76 | 109 | 29.52 | 257 |
| bengaluru | 2025 | 38.00 | 109 | 25.72 | 256 |
| chennai | 2016 | 64.67 | 92 | 48.93 | 240 |
| chennai | 2017 | 49.88 | 102 | 47.91 | 253 |
| chennai | 2018 | 61.46 | 109 | 46.57 | 256 |
| chennai | 2019 | 51.88 | 109 | 39.25 | 256 |
| chennai | 2024 | 35.42 | 109 | 19.60 | 257 |
| chennai | 2025 | 45.74 | 109 | 24.44 | 256 |
| delhi | 2015 | 181.53 | 106 | 90.34 | 247 |
| delhi | 2016 | 233.30 | 109 | 94.39 | 255 |
| delhi | 2017 | 195.21 | 109 | 75.48 | 256 |
| delhi | 2018 | 201.81 | 109 | 78.39 | 256 |
| delhi | 2019 | 199.10 | 109 | 70.29 | 256 |
| delhi | 2024 | 198.79 | 109 | 63.77 | 257 |
| delhi | 2025 | 190.53 | 109 | 56.64 | 256 |
| hyderabad | 2016 | 75.68 | 93 | 39.96 | 235 |
| hyderabad | 2017 | 67.23 | 107 | 39.15 | 255 |
| hyderabad | 2018 | 62.51 | 109 | 34.89 | 256 |
| hyderabad | 2019 | 62.18 | 109 | 32.77 | 256 |
| hyderabad | 2024 | 41.16 | 109 | 27.43 | 257 |
| hyderabad | 2025 | 42.10 | 109 | 32.01 | 256 |
| jaipur | 2018 | 74.00 | 109 | 55.80 | 256 |
| jaipur | 2019 | 64.64 | 109 | 42.21 | 256 |
| kanpur | 2016 | 228.78 | 96 | 100.96 | 208 |
| kanpur | 2017 | 252.33 | 87 | 101.43 | 214 |
| kanpur | 2018 | 221.28 | 98 | 58.14 | 247 |
| kanpur | 2019 | 196.57 | 98 | 55.72 | 239 |
| kolkata | 2019 | 118.76 | 109 | 46.81 | 256 |
| kolkata | 2024 | 75.52 | 109 | 31.65 | 257 |
| kolkata | 2025 | 79.94 | 109 | 30.35 | 256 |
| lucknow | 2015 | 226.92 | 76 | 51.29 | 207 |
| lucknow | 2016 | 219.66 | 108 | 87.16 | 218 |
| lucknow | 2017 | 192.46 | 78 | 85.37 | 249 |
| lucknow | 2018 | 191.57 | 109 | 94.28 | 241 |
| lucknow | 2019 | 167.56 | 109 | 78.99 | 256 |
| mumbai | 2015 | 63.96 | 107 | 45.32 | 253 |
| mumbai | 2016 | 61.92 | 107 | 28.10 | 237 |
| mumbai | 2017 | 71.58 | 70 | 35.18 | 242 |
| mumbai | 2019 | 64.41 | 109 | 22.12 | 254 |
| mumbai | 2024 | 56.02 | 109 | 24.79 | 257 |
| mumbai | 2025 | 52.84 | 109 | 26.44 | 256 |
| patna | 2018 | 210.10 | 101 | 80.59 | 250 |
| patna | 2019 | 208.36 | 106 | 60.84 | 242 |
| pune | 2024 | 56.06 | 109 | 28.43 | 257 |
| pune | 2025 | 65.76 | 109 | 31.01 | 256 |

![Monthly climatology](../../data/results/2/monthly_climatology.png)

![Seasonal diurnal profiles](../../data/results/2/seasonal_diurnal.png)

![Diwali window](../../data/results/2/diwali_window.png)

Diwali uses the central official calendar's date for all cities; regional observance can differ. The −3/+3-day windows retain only valid daily measurements in eligible city-years. Dates and sources:

- 2015: 2015-11-11; [official calendar](https://surveyofindia.gov.in/files/RONo.10.pdf).

- 2016: 2016-10-30; [official calendar](https://nationalarchives.nic.in/sites/default/files/2023-07/holiday-list-2016-english_0_0.pdf).

- 2017: 2017-10-19; [official calendar](https://kandlacustoms.gov.in/wp-content/uploads/2017/04/Holidays-2017.pdf).

- 2018: 2018-11-07; [official calendar](https://surveyofindia.gov.in/files/Holiday%20List%202018.pdf).

- 2019: 2019-10-27; [official calendar](https://surveyofindia.gov.in/files/Holidays%202019.pdf).

- 2024: 2024-10-31; [official calendar](https://www.surveyofindia.gov.in/documents/circulars/document-82049-spg-ro8-19-12-2023.pdf).

- 2025: 2025-10-20; [official calendar](https://necouncil.gov.in/sites/default/files/nec%20cal%202025.pdf).


Descriptive change compares equal-weight eligible annual means in the two observed eras. 95% intervals use 500 fixed-seed year-and-seven-day-block resamples of measured days. They omit structural uncertainty from stations, source conventions and non-random missingness; none of these comparisons is a causal policy effect.

| City | Status | 2015–2019 | 2024–2025 | Recent − baseline | 95% low | 95% high |
| --- | --- | --- | --- | --- | --- | --- |
| ahmedabad | unavailable | — | — | — | — | — |
| bengaluru | descriptive | 36.50 | 30.83 | -5.67 | -11.24 | -0.72 |
| chennai | descriptive | 48.95 | 27.55 | -21.40 | -27.90 | -13.95 |
| delhi | descriptive | 117.79 | 100.30 | -17.49 | -35.67 | 1.80 |
| hyderabad | descriptive | 45.55 | 33.27 | -12.28 | -17.76 | -6.96 |
| jaipur | unavailable | — | — | — | — | — |
| kanpur | unavailable | — | — | — | — | — |
| kolkata | descriptive | 68.30 | 44.94 | -23.36 | -39.11 | -8.07 |
| lucknow | unavailable | — | — | — | — | — |
| mumbai | descriptive | 41.91 | 34.20 | -7.71 | -14.94 | 0.64 |
| patna | unavailable | — | — | — | — | — |
| pune | unavailable | — | — | — | — | — |

## Meteorological normalisation

[Grange et al. 2018](https://doi.org/10.5194/acp-18-6223-2018) motivates the random forest. This implementation adapts the daily Swiss PM10 method to hourly Indian city PM2.5. Like [rmweather](https://github.com/skgrange/rmweather), it resamples joint weather and seasonal covariates while keeping date trend fixed. At least 300 observed donor draws are used with fixed seed; common random numbers and exact forest trend partitions avoid redundant predictions. Only existing eligible city-year hours with complete weather train/normalise. No imputation, forecast or target in the 2020–2023 gap is created. BLH is included if available; its January–June 2024 nulls remove those targets rather than fill them.

Validation fits only the earlier 80% of observed complete-case hours, with a seven-day purge before the final 20% holdout. The final historical normalisation model then refits on all available eligible complete-case hours; holdout metrics always come from the separate validation model. Permutation importance on held-out data, parameters and versions are in each city_model.json.

| City | Blocked R² | RMSE µg/m³ | Bias | Train hours | Holdout hours | Readiness screen |
| --- | --- | --- | --- | --- | --- | --- |
| ahmedabad | -1.96 | 56.32 | 38.65 | 12891 | 3262 | False |
| bengaluru | -0.01 | 13.89 | 4.95 | 42357 | 10632 | False |
| chennai | 0.14 | 19.73 | 2.13 | 37654 | 9456 | False |
| delhi | 0.38 | 74.12 | 11.29 | 45224 | 11348 | False |
| hyderabad | -0.71 | 13.02 | 5.45 | 37848 | 9505 | False |
| jaipur | 0.15 | 33.17 | -7.21 | 13838 | 3502 | False |
| kanpur | 0.60 | 56.18 | 18.33 | 25473 | 6402 | False |
| kolkata | 0.63 | 22.83 | -6.89 | 17373 | 4386 | False |
| lucknow | 0.37 | 54.71 | 24.93 | 31836 | 8001 | False |
| mumbai | 0.43 | 15.77 | 4.72 | 37025 | 9299 | False |
| patna | 0.25 | 85.50 | 29.37 | 13380 | 3387 | False |
| pune | 0.38 | 29.12 | -6.15 | 10368 | 2635 | False |

Held-out permutation importance: three largest mean decreases in R² per city. All features and five-repeat standard deviations are in each city_model.json. Correlated predictors share importance; these values are not causal contributions.

| City | Feature | Mean ΔR² | SD |
| --- | --- | --- | --- |
| ahmedabad | day_of_year_cos | 0.73 | 0.01 |
| ahmedabad | hour_sin | 0.11 | 0.01 |
| ahmedabad | day_of_year_sin | 0.08 | 0.01 |
| bengaluru | day_of_year_cos | 0.36 | 0.02 |
| bengaluru | wind_direction_sin | 0.32 | 0.01 |
| bengaluru | wind_speed_ms | 0.28 | 0.01 |
| chennai | day_of_year_cos | 0.62 | 0.03 |
| chennai | wind_direction_cos | 0.08 | 0.00 |
| chennai | surface_pressure_hpa | 0.03 | 0.00 |
| delhi | day_of_year_cos | 0.82 | 0.02 |
| delhi | day_of_year_sin | 0.31 | 0.01 |
| delhi | wind_direction_sin | 0.05 | 0.00 |
| hyderabad | day_of_year_cos | 0.36 | 0.04 |
| hyderabad | hour_sin | 0.04 | 0.00 |
| hyderabad | solar_radiation_wm2 | 0.03 | 0.00 |
| jaipur | day_of_year_cos | 0.09 | 0.00 |
| jaipur | boundary_layer_height_m | 0.03 | 0.00 |
| jaipur | total_cloud_cover | -0.01 | 0.00 |
| kanpur | day_of_year_cos | 0.63 | 0.02 |
| kanpur | day_of_year_sin | 0.10 | 0.01 |
| kanpur | boundary_layer_height_m | 0.10 | 0.01 |
| kolkata | day_of_year_cos | 0.60 | 0.01 |
| kolkata | hour_sin | 0.05 | 0.00 |
| kolkata | temperature_c | 0.04 | 0.00 |
| lucknow | day_of_year_cos | 0.63 | 0.02 |
| lucknow | day_of_year_sin | 0.31 | 0.01 |
| lucknow | boundary_layer_height_m | 0.07 | 0.01 |
| mumbai | day_of_year_cos | 1.18 | 0.02 |
| mumbai | wind_direction_cos | 0.02 | 0.00 |
| mumbai | total_cloud_cover | 0.01 | 0.00 |
| patna | day_of_year_cos | 0.35 | 0.02 |
| patna | hour_sin | 0.05 | 0.01 |
| patna | wind_speed_ms | 0.02 | 0.00 |
| pune | day_of_year_cos | 0.44 | 0.02 |
| pune | temperature_c | 0.06 | 0.00 |
| pune | solar_radiation_wm2 | 0.04 | 0.00 |

The readiness screen was defined before results: R²≥0.5, RMSE≤50% of holdout mean, absolute bias≤10% of holdout mean, at least 2,000 train and 1,000 test hours. This is a practical screen, not proof that a model or a causal research design is reliable. Cities with only one observed era cannot support an old/recent comparison.

![Raw and deweathered series](../../data/results/2/raw_deweathered_monthly.png)

Daily/monthly outputs preserve the same completeness thresholds. sampling_se is Monte Carlo sampling error, not total model/measurement uncertainty. All CSVs, models, SVG/PNG figures and hashes are under data/results/2/. Keep manifest.json eligible for version control.

## Reproducibility and limitations

```json
{
  "seed": 42,
  "n_trees": 100,
  "versions": {
    "numpy": "2.5.3",
    "scipy": "1.18.1",
    "Django": "5.2.18",
    "pandas": "2.3.3",
    "matplotlib": "3.11.2",
    "scikit-learn": "1.9.1"
  },
  "git_state": "versioned",
  "n_samples": 300,
  "code_sha256": "30cdb2ccf89c614e917c88bd7a77dfb60b9985c9fdd05cb8b4c0d1a3eafc5ed0",
  "eligibility": "75% valid calendar hours and days; daily18/monthly75%",
  "model_validation": "chronological80/20 with seven-day purge",
  "readiness_screen": {
    "r2_min": 0.5,
    "test_min": 1000,
    "train_min": 2000,
    "relative_rmse_max": 0.5,
    "absolute_relative_bias_max": 0.1
  },
  "export_revision": {
    "git_commit": "7e0adff38a82580bfef799dfa9fde2d867c47065",
    "code_sha256": "017584a496a10e9f5679f01d97ab6b69d7baf260225ce4c96b3c8ded42554864",
    "started_at": "2026-10-08T15:47:41.867965+00:00",
    "reason": "Correct only figure axis bounds, empty panels, distinct city colours and report export provenance; data and fitted models unchanged",
    "finished_at": "2026-10-08T15:47:58.166989+00:00"
  }
}
```

Recorded Git commit: `2b0f254ce0ddff9751019c1277ca5ac0e7194726`. Figure/report export commit: `7e0adff38a82580bfef799dfa9fde2d867c47065`. The source-code SHA256 and installed library versions are also stored with the run. Fixed seeds cannot remove changes in inputs or libraries.

2020–2023/2026 concentration coverage is absent or negligible. Historical observations are PM2.5 only. Site networks and provider compilations differ between eras; changing station contributions can change city means. Coverage is not representativeness. Some raw source rows have suspicious column/value jumps. Positive flatlines and PM inversions are diagnostic flags, not confirmed equipment faults. Public ERA5 is reanalysis at approximate city centres and has variable-specific nulls. Whole-case selection introduces selection bias. The city-year eligibility rule does not guarantee every season is equally represented. RF normalisation cannot identify a policy effect or remove all emission/chemistry confounding.

Phase 3B should validate provider time conventions and station metadata, examine station-network sensitivity, assess season-specific holdout errors and review source anomalies before selecting research designs. Do not use before/after differences as causal estimates. Forecasting, RAG, simulators and dashboards remain outside this phase.

## Final live verification

Run 2 and Celery task `a0588198-5fb5-4478-8430-fec71e561947` succeeded. Its measured
analysis duration was 1311.729 seconds. An idempotent full repeat
changed **0** further flags; the initial **12,498** corrections
and pre-correction rates are preserved explicitly from Run 1. The complete
**16,266,240**-row measurement/provenance fingerprint is unchanged.

- Full unchanged-baseline plus analytics suite: **110 passed, 1 warning in 50.62s**.
- Ruff: **All checks passed; 135 files already formatted**.
- Strict OpenAPI validation: **exit 0**. Production deployment check: **no issues/warnings**.
- Health: **HTTP 200**, database/extensions/Redis/Celery all true.
- **103** real HTTP checks cover every city, raw/deweathered daily/monthly
  series, missing weather, gap queries and read-only/error responses.
- **57** CSV exports and all **12** model score sets
  reproduce within 1e-10 numerical tolerance.
- All **99** original Run 2 artifact sizes/hashes verified before
  supplemental validation evidence was added to the manifest.
- **0** deweathered rows in 2020-2023; no 2026 predictions.

The known NetCDF/NumPy `numpy.ndarray size changed` RuntimeWarning remains visible
(Expected 16 from C header, got 96 from PyObject). It was not filtered.

The PowerShell wrapper initially misclassified a Matplotlib INFO line on native
stderr as failure, even though the real Celery job succeeded. It now preserves
stderr and uses the process exit code. A fresh-font-cache probe plus explicit
stderr returned 0, while an exit-7 probe still raised a failure. The corrected
`run_phase3a --help` command returns 0. Empty plot panels now explicitly show
"No observed series" on the correct era axes; annual panels do not include the
gap. Figures/report were regenerated from the unchanged saved Run 2 outputs; the
separate export revision and times are recorded above.

Actual logs, the verifier, a report snapshot and `verification.json` are stored
with the CSVs/figures under `data/results/2/`; its SHA256 manifest includes that
evidence. Original tests retain all 13 baseline source hashes. No additional manual
setup action is needed. None of the 12 city models passed the predefined
normalisation readiness screen.

![Annual means in the two observed eras](../../data/results/2/annual_pm25.png)

![Flag rates before/after the audit](../../data/results/2/flag_rates.png)
