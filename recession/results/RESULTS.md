# Recession Alert history test

Run 2026-11-28, data through 2026-10. Settings picked on 1968-1999 only; judged on 2000-2026.
**Chosen settings:** credit spread up 0.50 pts from its 12-month low; jobless claims 15% above their 52-week low; signal must last 2 month(s).
**Versions tried:** 24. Real-time payroll data starts 1955-05-06.

## NEWER years (the real test)

### WARNING (2+ early signals)
- Recessions: 2001-04 (7 mo early), 2008-01 (1 mo early), 2020-03 (MISSED)
- False alarms (3): 2010-09 to 2010-10, 2023-07 to 2023-08, 2024-07 to 2024-10
- Too early to judge: 2026-01 to 2026-01

### Baseline: yield curve alone
- Recessions: 2001-04 (8 mo early), 2008-01 (17 mo early), 2020-03 (9 mo early)
- False alarms (1): 2022-11 to 2025-10
- Too early to judge: none

### WATCH (1+ early signal)
- Recessions: 2001-04 (11 mo early), 2008-01 (16 mo early), 2020-03 (14 mo early)
- False alarms (5): 2005-10 to 2005-10, 2011-09 to 2012-06, 2015-07 to 2016-03, 2022-08 to 2022-08, 2022-12 to 2025-10
- Too early to judge: 2026-01 to 2026-01

### RECESSION SIGNAL (Sahm Rule or falling jobs)
- Recessions: 2001-04 (1 mo after start), 2008-01 (2 mo after start), 2020-03 (1 mo after start)
- False alarms (2): 2010-09 to 2010-10, 2024-08 to 2024-10

## OLDER years (used to pick settings)

### WARNING (2+ early signals)
- Recessions: 1970-01 (2 mo early), 1973-12 (1 mo early), 1980-02 (6 mo early), 1981-08 (24 mo early), 1990-08 (8 mo early)
- False alarms (1): 1976-12 to 1976-12
- Too early to judge: none

### Baseline: yield curve alone
- Recessions: 1970-01 (12 mo early), 1973-12 (6 mo early), 1980-02 (14 mo early), 1981-08 (24 mo early), 1990-08 (MISSED)
- False alarms (0): none
- Too early to judge: none

### WATCH (1+ early signal)
- Recessions: 1970-01 (5 mo early), 1973-12 (5 mo early), 1980-02 (13 mo early), 1981-08 (24 mo early), 1990-08 (13 mo early)
- False alarms (8): 1976-10 to 1976-10, 1976-12 to 1976-12, 1984-09 to 1985-01, 1985-04 to 1985-06, 1986-01 to 1986-04, 1986-08 to 1986-12, 1988-02 to 1988-02, 1998-10 to 1999-05
- Too early to judge: none

### RECESSION SIGNAL (Sahm Rule or falling jobs)
- Recessions: 1970-01 (2 mo before start), 1973-12 (4 mo after start), 1980-02 (3 mo after start), 1981-08 (3 mo before start), 1990-08 (2 mo after start)
- False alarms (1): 1976-12 to 1976-12

## All versions on the newer years

| spread | claims | months | old caught | old false | new caught | new false | new undecided |
|---|---|---|---|---|---|---|---|
| 0.50 | 15% | 1 | 5 | 3 | 3 | 4 | 1 |
| 0.50 | 15% | 2 | 5 | 1 | 2 | 3 | 1 |
| 0.50 | 20% | 1 | 5 | 1 | 3 | 4 | 1 |
| 0.50 | 20% | 2 | 4 | 1 | 2 | 2 | 1 |
| 0.50 | 25% | 1 | 4 | 1 | 3 | 3 | 1 |
| 0.50 | 25% | 2 | 4 | 1 | 2 | 2 | 1 |
| 0.50 | 30% | 1 | 4 | 1 | 3 | 2 | 1 |
| 0.50 | 30% | 2 | 4 | 1 | 2 | 2 | 1 |
| 0.75 | 15% | 1 | 4 | 1 | 3 | 4 | 1 |
| 0.75 | 15% | 2 | 3 | 1 | 1 | 3 | 1 |
| 0.75 | 20% | 1 | 3 | 1 | 2 | 4 | 1 |
| 0.75 | 20% | 2 | 3 | 1 | 1 | 2 | 1 |
| 0.75 | 25% | 1 | 3 | 1 | 2 | 3 | 1 |
| 0.75 | 25% | 2 | 2 | 1 | 1 | 2 | 1 |
| 0.75 | 30% | 1 | 3 | 1 | 2 | 2 | 1 |
| 0.75 | 30% | 2 | 2 | 1 | 1 | 2 | 1 |
| 1.00 | 15% | 1 | 4 | 1 | 2 | 4 | 1 |
| 1.00 | 15% | 2 | 3 | 1 | 1 | 3 | 1 |
| 1.00 | 20% | 1 | 3 | 1 | 1 | 4 | 1 |
| 1.00 | 20% | 2 | 3 | 1 | 1 | 2 | 1 |
| 1.00 | 25% | 1 | 3 | 1 | 1 | 3 | 1 |
| 1.00 | 25% | 2 | 2 | 1 | 1 | 2 | 1 |
| 1.00 | 30% | 1 | 3 | 1 | 1 | 2 | 1 |
| 1.00 | 30% | 2 | 2 | 1 | 1 | 2 | 1 |

## Every change of alert level since 2000

| month | level | in recession |
|---|---|---|
| 2000-01 | ALL CLEAR | no |
| 2000-05 | WATCH | no |
| 2000-09 | RECESSION SIGNAL | no |
| 2000-10 | WARNING | no |
| 2001-05 | RECESSION SIGNAL | yes |
| 2003-11 | ALL CLEAR | no |
| 2005-10 | WATCH | no |
| 2005-11 | ALL CLEAR | no |
| 2006-09 | WATCH | no |
| 2007-12 | WARNING | no |
| 2008-03 | RECESSION SIGNAL | yes |
| 2010-07 | WATCH | no |
| 2010-09 | RECESSION SIGNAL | no |
| 2010-11 | WATCH | no |
| 2010-12 | ALL CLEAR | no |
| 2011-09 | WATCH | no |
| 2012-07 | ALL CLEAR | no |
| 2015-07 | WATCH | no |
| 2016-04 | ALL CLEAR | no |
| 2019-01 | WATCH | no |
| 2019-02 | ALL CLEAR | no |
| 2019-07 | WATCH | no |
| 2020-04 | RECESSION SIGNAL | yes |
| 2021-05 | ALL CLEAR | no |
| 2022-08 | WATCH | no |
| 2022-09 | ALL CLEAR | no |
| 2022-12 | WATCH | no |
| 2023-07 | WARNING | no |
| 2023-09 | WATCH | no |
| 2024-07 | WARNING | no |
| 2024-08 | RECESSION SIGNAL | no |
| 2024-11 | WATCH | no |
| 2025-11 | ALL CLEAR | no |
| 2026-01 | RECESSION SIGNAL | no |
| 2026-02 | ALL CLEAR | no |
