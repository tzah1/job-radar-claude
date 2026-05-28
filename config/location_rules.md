# Location Rules — Job Radar v1

## Preferred Work Model
Hybrid (mix of office and remote days)

## Geographic Range

### Preferred Zone (full score)
- Tel Aviv
- Herzliya (north limit)
- Petah Tikva
- Ramat Gan
- Givatayim
- Bnei Brak
- Holon
- Bat Yam

### Acceptable Zone (neutral score impact)
- Modi'in (east limit)
- Rehovot
- Rishon LeZion
- Yavne (south limit)

### Outside Range (score reduction if no remote)
- Haifa and north
- Beer Sheva and south
- Jerusalem and east
- Eilat

## Remote / Flexibility Rules
- **Fully remote**: positive signal (+score), acceptable anywhere in Israel
- **Hybrid**: strong positive when in preferred zone
- **Remote-first with occasional office**: positive
- **Fully onsite outside preferred zone**: reduce score significantly
- **Parent-friendly flexibility**: strong positive — explicitly mentioned flexibility
  for parents, school hours, or family commitments is a meaningful signal

## Scoring Implementation
See `config/scoring_rules.md` for the numeric adjustments.
Location detection is keyword-based on the `location` and `work_model` fields.
When these fields are empty, location score is neutral.

## Note on Manual Entries
When manually entering jobs under `data/raw/manual/`, always fill in:
- `location`: city name (e.g., "Tel Aviv", "Herzliya")
- `work_model`: one of "hybrid", "remote", "onsite", "remote-first"
