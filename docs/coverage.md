# Coverage: can we answer what people ask? (run 20261020s)

Do the Wikibase items and the statute index hold the facts each question needs (who, steps, deadline, fee, form, where, appeal)?  `A` adequate, `P` partial, `D` partial on draft process items alone (a `single` state model or an asked answer's draft; never more than partial), `-` none; the kinds still missing follow the verdict.  `lexflow run coverage --states va,dc` regenerates this file (lexflow/ask/coverage.py); `lexflow run coverage --fill` answers the gap cells with the ask pipeline and stores the drafts (`--cells filled --model <other>` answers the filled cells again with another model, beside the first answers, for a comparison).

| Column | Cells | Adequate | Partial | Draft | None | Top missing kinds | Ollama cells | Composite | Vital recall | Citation precision | s/cell | s/Ollama cell |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dc | 49 | 2 | 46 | 31 | 1 | who (36), fee (28), form (22), where (15) | 12 | 0.471 | 0.34 | 0.226 | 35.894 | 146.242 |
| va | 49 | 3 | 45 | 31 | 1 | who (36), fee (26), form (22), where (15) | 12 | 0.417 | 0.264 | 0.23 | 67.784 | 276.392 |

| Question | dc | va |
|---|---|---|
| public_records | P who (0.8761) | A (0.7853) |
| foia_appeal | P who (0.8221) | P who (0.5546) |
| police_incident_records | P who (0.4113) | P who,fee (0.3867) |
| start_llc | P fee,form (0.4012) | P form (0.4451) |
| business_license | P fee (0.3358) | P fee (0.1765) |
| business_closure | P fee,form (0.3529) | P form (0.6876) |
| nonprofit_formation | P fee,form (0.1765) | P form (0.0) |
| procurement_bids | A (0.6237) | A (0.5294) |
| short_term_rental | P (0.3901) | P (0.5308) |
| building_permit | D who,fee,form,where (0.1765) | D who,fee,form,where (0.3529) |
| zoning_variance | D fee (0.732) | D who,fee,appeal (0.3806) |
| noise_complaint | D who,where | D who,where (0.1765) |
| property_tax_appeal | D who,appeal,where (0.3529) | D who,appeal,where |
| property_tax_pay | D who,where,fee | D who,where,fee |
| vehicle_registration | D who,fee,where | D who,fee,where |
| meals_tax | P fee,form | P fee,form |
| voter_registration | D who,form,where | D who,deadline,form,where |
| absentee_voting | D who,form | D who,deadline,form |
| dog_license | D who,fee,form,deadline | D who,fee,form |
| marriage_license | D who,fee,where,form | D who,fee,where,form |
| parking_ticket | D who,appeal,fee | D who,appeal,fee |
| traffic_ticket | D who,appeal | D who,appeal |
| small_claims | D who,fee,where,form | D who,fee,where,form |
| probate | D who,fee,where | D who,fee,where |
| eviction | D who,appeal | D who,appeal |
| name_change | D who,fee,form,where | D who,fee,form,where |
| benefits_apply | D who,where,form | D who,where,form |
| unemployment_appeal | D who,appeal,form | D who,appeal,form |
| expungement | D who,fee,form,where,appeal | D who,fee,form,where,appeal |
| concealed_carry | D who,fee,form,appeal | D who,fee,form,appeal |
| child_care_license | D who,fee,form,appeal | D who,fee,form,appeal |
| contractor_license | D who,fee,form | D who,fee,form |
| license_denial_appeal | D who,appeal | D who,appeal |
| open_meetings | P who | P who |
| public_comment | P who,where | P who,where |
| deed_recording | - who,steps,fee,where | - who,steps,fee,where |
| glass_studio | P fee,form | P fee,form |
| glass_q1 | D who,fee,form | D who,fee,form |
| glass_q2 | D who,where,appeal | D who,where,appeal |
| glass_q3 | D who | D who |
| glass_q4 | A | A |
| glass_q5 | D who,fee,form | D who,fee,form |
| glass_q6 | P fee | P fee |
| glass_q7 | P fee | P fee |
| glass_q8 | D who,form | D who,form |
| glass_q9 | P fee,form | P fee,form |
| glass_q10 | D who,fee,appeal | D who,fee,appeal |
| glass_q11 | D who | D who |
| glass_q12 | D who,fee,appeal | D who,fee,appeal |

Totals: 5 adequate, 91 partial (of them 62 on drafts alone), 2 none over 98 cells.
