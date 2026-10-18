# Sources and licences

Checked 2026-10-18. Re-check before each re-ingest; record the fetch date on every source row.

| Source | Licence | Required attribution |
|---|---|---|
| Residential Tenancies and Rooming Accommodation Act 2008 (Qld), current reprint, legislation.qld.gov.au | CC BY 4.0 | "Based on content from the Queensland Legislation website at [date]. For the latest information on Queensland Government legislation please go to https://www.legislation.qld.gov.au." |
| RTA Queensland renting guidance, rta.qld.gov.au | CC BY 3.0 AU (with exclusions: RTA logo, trade marks, third-party content; the site disclaimer also applies) | "© The State of Queensland Residential Tenancies Authority" |

Both attributions must appear in the app footer and on every exported report.

Still to check before fetching: robots.txt for both sites, and that the Act page used is the
current in-force reprint (Queensland rental law changed in 2024 and 2025).

## Bundled files

- `data/forms/form18a.pdf`: RTA General tenancy agreement (Form 18a), v23 Sep25, from
  rta.qld.gov.au. CC BY 3.0 AU, © The State of Queensland Residential Tenancies Authority.
  Used to read real leases and to build the sample leases in `eval/leases/`, which are filled
  with made-up names and planted special terms.
