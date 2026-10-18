# Coverage: can we answer what people ask? (run 20261018b)

Do the Wikibase items and the statute index hold the facts each question needs (who, steps, deadline, fee, form, where, appeal)?  `A` adequate, `P` partial, `D` partial on draft process items alone (a `single` state model or an asked answer's draft; never more than partial), `-` none; the kinds still missing follow the verdict.  `lexflow run coverage --states va,dc` regenerates this file (lexflow/ask/coverage.py); `lexflow run coverage --fill` answers the gap cells with the ask pipeline and stores the drafts.

| Column | Cells | Adequate | Partial | Draft | None | Top missing kinds | Ollama cells | Composite | Vital recall | Citation precision | s/cell | s/Ollama cell |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dc | 36 | 1 | 34 | 23 | 1 | who (28), fee (20), form (17), where (14) | 12 | 0.471 | 0.34 | 0.226 | 243.353 | 729.342 |
| va | 36 | 2 | 33 | 23 | 1 | who (28), fee (18), form (17), where (14) | 12 | 0.417 | 0.264 | 0.23 | 36.917 | 110.3 |
| va/47100200200000 | 27 | 25 | 1 | 1 | 1 | fee (2), who (2), appeal (1), form (1) | 0 | - | - | - | 0.5 | - |
| va/47210400100000 | 27 | 23 | 3 | 0 | 1 | fee (3), who (3), where (2), steps (1) | 0 | - | - | - | 0.478 | - |
| va/47213000100000 | 27 | 25 | 1 | 1 | 1 | fee (1), form (1), steps (1), where (1) | 0 | - | - | - | 0.881 | - |

| Question | dc | va | va/47100200200000 | va/47210400100000 | va/47213000100000 |
|---|---|---|---|---|---|
| public_records | P who (0.8761) | A (0.7853) | A | P fee | A |
| foia_appeal | P who (0.8221) | P who (0.5546) | A | A | A |
| police_incident_records | P who (0.4113) | P who,fee (0.3867) | A | P who,fee | A |
| start_llc | P fee,form (0.4012) | P form (0.4451) |  |  |  |
| business_license | P fee (0.3358) | P fee (0.1765) | A | A | A |
| business_closure | P fee,form (0.3529) | P form (0.6876) |  |  |  |
| nonprofit_formation | P fee,form (0.1765) | P form (0.0) |  |  |  |
| procurement_bids | A (0.6237) | A (0.5294) | A | A | A |
| short_term_rental | P (0.3901) | P (0.5308) | A | A | A |
| building_permit | D who,fee,form,where (0.1765) | D who,fee,form,where (0.3529) | A | A | A |
| zoning_variance | D fee (0.732) | D who,fee,appeal (0.3806) | A | A | A |
| noise_complaint | D who,where | D who,where (0.1765) | A | A | A |
| property_tax_appeal | D who,appeal,where (0.3529) | D who,appeal,where | A | A | A |
| property_tax_pay | D who,where,fee | D who,where,fee | A | A | A |
| vehicle_registration | D who,fee,where | D who,fee,where | A | A | A |
| meals_tax | P fee,form | P fee,form | A | A | A |
| voter_registration | D who,form,where | D who,deadline,form,where | A | A | A |
| absentee_voting | D who,form | D who,deadline,form | A | A | A |
| dog_license | D who,fee,form,deadline | D who,fee,form | A | A | A |
| marriage_license | D who,fee,where,form | D who,fee,where,form | A | A | A |
| parking_ticket | D who,appeal,fee | D who,appeal,fee | A | A | A |
| traffic_ticket | D who,appeal | D who,appeal | A | A | A |
| small_claims | D who,fee,where,form | D who,fee,where,form | A | A | A |
| probate | D who,fee,where | D who,fee,where | A | A | A |
| eviction | D who,appeal | D who,appeal | A | A | A |
| name_change | D who,fee,form,where | D who,fee,form,where |  |  |  |
| benefits_apply | D who,where,form | D who,where,form | A | A | D form |
| unemployment_appeal | D who,appeal,form | D who,appeal,form |  |  |  |
| expungement | D who,fee,form,where,appeal | D who,fee,form,where,appeal |  |  |  |
| concealed_carry | D who,fee,form,appeal | D who,fee,form,appeal | D who,fee,form,appeal | A | A |
| child_care_license | D who,fee,form,appeal | D who,fee,form,appeal |  |  |  |
| contractor_license | D who,fee,form | D who,fee,form |  |  |  |
| license_denial_appeal | D who,appeal | D who,appeal |  |  |  |
| open_meetings | P who | P who | A | A | A |
| public_comment | P who,where | P who,where | A | P who,where | A |
| deed_recording | - who,steps,fee,where | - who,steps,fee,where | - who,steps,fee,where | - who,steps,fee,where | - who,steps,fee,where |

Totals: 76 adequate, 72 partial (of them 48 on drafts alone), 5 none over 153 cells.
