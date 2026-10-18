# Demo bills (follow-up questions)

Load with `POST /api/upload/sample {"sample_id": "DEMO-001"}` or upload `data/demo_bills.pdf` to `POST /api/upload/pdf` with `account=DEMO-001`. Send answers to `POST /api/upload/review`.

| Bill | What the engine finds | Questions it triggers | Demo answer that creates an `answer_mismatch` flag |
|---|---|---|---|
| DEMO-001 | nothing (bill math is clean) | room nights (4 days), ER visit, X-ray ×2, medicine, supplies | room_nights = 3 → "You said 3 nights, but the bill charges 4 room days." |
| DEMO-002 | duplicate CMP (lines 6 & 7) | ICU nights (2), ER visit, ambulance ride, ambulance miles (25), blood draws (6) | ambulance_miles = 10 (under 80% of 25), blood_draws = "Seems like too many" |
| DEMO-003 | line math error on crutches (line 4: 1 × $85 shows $95) | room nights (3), private room, therapy (60 min), surgical tray, crutches (the $45 TV rental is 6th by line total, so the max-5 rule leaves it out) | private_room = "No", therapy_time:97110 = "Shorter than that" |
| DEMO-004 | nothing | observation (18 h), blood transfusion, ER visit, procedure (splint) | blood_transfusion = "No" |