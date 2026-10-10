# Research library consulted in Phase 3B

The retained source documents are under `data/raw/research_library/` on D:.
[RESEARCH_LIBRARY.json](RESEARCH_LIBRARY.json) records the download URL, local
path, byte size and SHA-256 for each cached document. These are source documents,
not a RAG index. The paper cites only this library or research documents already
listed in the project documentation.

| Document | Primary source | Use |
| --- | --- | --- |
| Grange et al. 2018, *Random forest meteorological normalisation models for Swiss PM10 trend analysis* | [Atmospheric Chemistry and Physics](https://acp.copernicus.org/articles/18/6223/2018/) | RF normalisation and calendar/weather predictors; published work concerns PM10, not a validation guarantee for these Indian PM2.5 series |
| Shi et al. 2021, *Abrupt but smaller than expected changes in surface air quality attributable to COVID-19 lockdowns* | [Author-hosted paper](https://pure-oai.bham.ac.uk/ws/files/114238854/eabd6696.full.pdf) | Cautious intervention interpretation and the need for observations around interventions |
| CPCB, *List of 131 Non-Attainment cities* | [Official PDF](https://cpcb.gov.in/uploads/Non-Attainment_Cities.pdf) | City status, including the starred million-plus footnote; Chennai is a participant outside the non-attainment classification |
| NCAP official statement, 23 March 2023 | [PIB](https://www.pib.gov.in/PressReleasePage.aspx?PRID=1909910&lang=2&reg=48) | PM10 target and fiscal-year 2017–18 baseline |
| NCAP update, 28 November 2024 | [PIB](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2078363&lang=2&reg=48) | Programme update and Hyderabad–Patancheru urban-area merger |
| NCAP update, 23 July 2026 | [PIB](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2288316&lang=1&reg=48) | Current official programme context, distinct from project results |
| NCAP National Apex Committee minutes | [PRANA PDF](https://prana.cpcb.gov.in/ncapDashboard/download_public_portal_file/Minutes_of_National_Apex_Committee_meeting.pdf) | Programme context |
| WHO Global Air Quality Guidelines 2021 | [WHO](https://www.who.int/publications/i/item/9789240034228/) | Guideline context; population exposure or health effects are not estimated |
| CPCB National Air Quality Index | [CPCB](https://cpcb.gov.in/National-Air-Quality-Index/) | Distinguishing pollutant concentrations from an AQI index |

The first automated Shi download used the wrong PMC identifier. Title/DOI
verification caught it before interpretation. The verified replacement has DOI
`10.1126/sciadv.abd6696`, PMCID `PMC7806219`; its cached PDF and hash are catalogued.
The unrelated initial HTML is excluded from the consulted library manifest.
