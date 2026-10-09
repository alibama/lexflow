{Q:jurisdiction:va/albemarle_county}	P8	"https://www.wikidata.org/wiki/Q488653"
{Q:process:va-albemarle-17-211-compiled}	P5	Q7
{Q:process:va-albemarle-17-211-compiled}	P15	{Q:jurisdiction:va/albemarle_county}
{Q:process:va-albemarle-17-211-compiled}	{P:wiki_page}	"https://lexipedia.xyz/doku.php?id=process:va:albemarle_county:17-211-compiled"
{Q:process:va-albemarle-17-211-compiled}	{P:bpmn_model}	"https://lexipedia.xyz/lib/exe/fetch.php?media=process:va:albemarle_county:17-211-compiled.bpmn"
{Q:process:va-albemarle-17-211-compiled}	{P:dmn_model}	"https://lexipedia.xyz/lib/exe/fetch.php?media=process:va:albemarle_county:17-211-compiled.dmn"
{Q:provision:va/albemarle_county:17-211}	P5	Q10
{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211"
{Q:provision:va/albemarle_county:17-211}	P25	"17-211"
{Q:provision:va/albemarle_county:17-211}	P23	"https://library.municode.com/va/albemarle_county/codes/code_of_ordinances"
{Q:provision:va/albemarle_county:17-211}	{P:wiki_page}	"https://lexipedia.xyz/doku.php?id=law:va:albemarle_county:17-211"
{Q:provision:va/albemarle_county:17-211}	P15	{Q:jurisdiction:va/albemarle_county}
{Q:provision:va/albemarle_county:17-211}	P24	+2014-07-01T00:00:00Z/11	P25	"Ord. 14-17(1)"
{Q:process:va-albemarle-17-211-compiled}	P13	{Q:provision:va/albemarle_county:17-211}
{Q:step:va-albemarle-17-211-compiled:start}	P5	Q8
{Q:step:va-albemarle-17-211-compiled:start}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:start}
{Q:step:va-albemarle-17-211-compiled:start}	{P:bpmn_element}	"start"
{Q:step:va-albemarle-17-211-compiled:start}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:county}
{Q:step:va-albemarle-17-211-compiled:start}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211-compiled:file_request_wait}	P5	Q9
{Q:step:va-albemarle-17-211-compiled:file_request_wait}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:file_request_wait}
{Q:step:va-albemarle-17-211-compiled:file_request_wait}	{P:bpmn_element}	"file_request_wait"
{Q:step:va-albemarle-17-211-compiled:file_request_wait}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:clerk}
{Q:step:va-albemarle-17-211-compiled:file_request}	P5	Q8
{Q:step:va-albemarle-17-211-compiled:file_request}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:file_request}
{Q:step:va-albemarle-17-211-compiled:file_request}	{P:bpmn_element}	"file_request"
{Q:step:va-albemarle-17-211-compiled:file_request}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:appellant}
{Q:step:va-albemarle-17-211-compiled:file_request}	P16	Q14	P17	{Q:actor:va-albemarle-17-211-compiled:appellant}
{Q:step:va-albemarle-17-211-compiled:file_request}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211-compiled:file_request_timeout}	P5	Q8
{Q:step:va-albemarle-17-211-compiled:file_request_timeout}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:file_request_timeout}
{Q:step:va-albemarle-17-211-compiled:file_request_timeout}	{P:bpmn_element}	"file_request_timeout"
{Q:step:va-albemarle-17-211-compiled:file_request_timeout}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:clerk}
{Q:step:va-albemarle-17-211-compiled:file_request_timeout}	{P:time_limit}	"P30D"	{P:deadline_anchor}	"date of notice of the action"
{Q:step:va-albemarle-17-211-compiled:file_request_timeout}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)(1)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211-compiled:file_request_lapsed}	P5	Q8
{Q:step:va-albemarle-17-211-compiled:file_request_lapsed}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:file_request_lapsed}
{Q:step:va-albemarle-17-211-compiled:file_request_lapsed}	{P:bpmn_element}	"file_request_lapsed"
{Q:step:va-albemarle-17-211-compiled:file_request_lapsed}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:clerk}
{Q:step:va-albemarle-17-211-compiled:file_request_lapsed}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)(1)"	{P:grounding}	"implied"
{Q:step:va-albemarle-17-211-compiled:determine_standing}	P5	Q9
{Q:step:va-albemarle-17-211-compiled:determine_standing}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:determine_standing}
{Q:step:va-albemarle-17-211-compiled:determine_standing}	{P:bpmn_element}	"determine_standing"
{Q:step:va-albemarle-17-211-compiled:determine_standing}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:hearing_officer}
{Q:step:va-albemarle-17-211-compiled:determine_standing}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(B)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211-compiled:hold_hearing}	P5	Q8
{Q:step:va-albemarle-17-211-compiled:hold_hearing}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:hold_hearing}
{Q:step:va-albemarle-17-211-compiled:hold_hearing}	{P:bpmn_element}	"hold_hearing"
{Q:step:va-albemarle-17-211-compiled:hold_hearing}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:hearing_officer}
{Q:step:va-albemarle-17-211-compiled:hold_hearing}	P16	Q13	P17	{Q:actor:va-albemarle-17-211-compiled:hearing_officer}
{Q:step:va-albemarle-17-211-compiled:hold_hearing}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(2)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211-compiled:hold_hearing_deadline}	P5	Q8
{Q:step:va-albemarle-17-211-compiled:hold_hearing_deadline}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:hold_hearing_deadline}
{Q:step:va-albemarle-17-211-compiled:hold_hearing_deadline}	{P:bpmn_element}	"hold_hearing_deadline"
{Q:step:va-albemarle-17-211-compiled:hold_hearing_deadline}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:county}
{Q:step:va-albemarle-17-211-compiled:hold_hearing_deadline}	{P:time_limit}	"P30D"	{P:deadline_anchor}	"receipt of the petition requesting a hearing"
{Q:step:va-albemarle-17-211-compiled:hold_hearing_deadline}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(2)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211-compiled:hold_hearing_deadline_end}	P5	Q8
{Q:step:va-albemarle-17-211-compiled:hold_hearing_deadline_end}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:hold_hearing_deadline_end}
{Q:step:va-albemarle-17-211-compiled:hold_hearing_deadline_end}	{P:bpmn_element}	"hold_hearing_deadline_end"
{Q:step:va-albemarle-17-211-compiled:hold_hearing_deadline_end}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:hearing_officer}
{Q:step:va-albemarle-17-211-compiled:hold_hearing_deadline_end}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(2)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211-compiled:consider_evidence}	P5	Q8
{Q:step:va-albemarle-17-211-compiled:consider_evidence}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:consider_evidence}
{Q:step:va-albemarle-17-211-compiled:consider_evidence}	{P:bpmn_element}	"consider_evidence"
{Q:step:va-albemarle-17-211-compiled:consider_evidence}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:hearing_officer}
{Q:step:va-albemarle-17-211-compiled:consider_evidence}	P16	Q13	P17	{Q:actor:va-albemarle-17-211-compiled:hearing_officer}
{Q:step:va-albemarle-17-211-compiled:consider_evidence}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(3)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211-compiled:keep_record}	P5	Q8
{Q:step:va-albemarle-17-211-compiled:keep_record}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:keep_record}
{Q:step:va-albemarle-17-211-compiled:keep_record}	{P:bpmn_element}	"keep_record"
{Q:step:va-albemarle-17-211-compiled:keep_record}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:hearing_officer}
{Q:step:va-albemarle-17-211-compiled:keep_record}	P16	Q13	P17	{Q:actor:va-albemarle-17-211-compiled:hearing_officer}
{Q:step:va-albemarle-17-211-compiled:keep_record}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(4)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211-compiled:issue_decision}	P5	Q8
{Q:step:va-albemarle-17-211-compiled:issue_decision}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:issue_decision}
{Q:step:va-albemarle-17-211-compiled:issue_decision}	{P:bpmn_element}	"issue_decision"
{Q:step:va-albemarle-17-211-compiled:issue_decision}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:hearing_officer}
{Q:step:va-albemarle-17-211-compiled:issue_decision}	P16	Q13	P17	{Q:actor:va-albemarle-17-211-compiled:hearing_officer}
{Q:step:va-albemarle-17-211-compiled:issue_decision}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(F)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_wait}	P5	Q9
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_wait}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:appeal_to_court_wait}
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_wait}	{P:bpmn_element}	"appeal_to_court_wait"
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_wait}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:county}
{Q:step:va-albemarle-17-211-compiled:appeal_to_court}	P5	Q8
{Q:step:va-albemarle-17-211-compiled:appeal_to_court}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:appeal_to_court}
{Q:step:va-albemarle-17-211-compiled:appeal_to_court}	{P:bpmn_element}	"appeal_to_court"
{Q:step:va-albemarle-17-211-compiled:appeal_to_court}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:appellant}
{Q:step:va-albemarle-17-211-compiled:appeal_to_court}	P16	Q16	P17	{Q:actor:va-albemarle-17-211-compiled:appellant}
{Q:step:va-albemarle-17-211-compiled:appeal_to_court}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(F)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_timeout}	P5	Q8
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_timeout}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:appeal_to_court_timeout}
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_timeout}	{P:bpmn_element}	"appeal_to_court_timeout"
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_timeout}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:county}
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_timeout}	{P:time_limit}	"P30D"	{P:deadline_anchor}	"date of the hearing officer's written decision"
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_timeout}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(F)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_lapsed}	P5	Q8
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_lapsed}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:appeal_to_court_lapsed}
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_lapsed}	{P:bpmn_element}	"appeal_to_court_lapsed"
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_lapsed}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:county}
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_lapsed}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(F)"	{P:grounding}	"implied"
{Q:step:va-albemarle-17-211-compiled:transcribe}	P5	Q8
{Q:step:va-albemarle-17-211-compiled:transcribe}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:transcribe}
{Q:step:va-albemarle-17-211-compiled:transcribe}	{P:bpmn_element}	"transcribe"
{Q:step:va-albemarle-17-211-compiled:transcribe}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:county}
{Q:step:va-albemarle-17-211-compiled:transcribe}	P16	Q13	P17	{Q:actor:va-albemarle-17-211-compiled:county}
{Q:step:va-albemarle-17-211-compiled:transcribe}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(4)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211-compiled:determine_standing_gw}	P5	Q9
{Q:step:va-albemarle-17-211-compiled:determine_standing_gw}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:determine_standing_gw}
{Q:step:va-albemarle-17-211-compiled:determine_standing_gw}	{P:bpmn_element}	"determine_standing_gw"
{Q:step:va-albemarle-17-211-compiled:determine_standing_gw}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:hearing_officer}
{Q:step:va-albemarle-17-211-compiled:determine_standing_not_hold_hearing}	P5	Q8
{Q:step:va-albemarle-17-211-compiled:determine_standing_not_hold_hearing}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:determine_standing_not_hold_hearing}
{Q:step:va-albemarle-17-211-compiled:determine_standing_not_hold_hearing}	{P:bpmn_element}	"determine_standing_not_hold_hearing"
{Q:step:va-albemarle-17-211-compiled:determine_standing_not_hold_hearing}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:hearing_officer}
{Q:step:va-albemarle-17-211-compiled:transcribe_done}	P5	Q8
{Q:step:va-albemarle-17-211-compiled:transcribe_done}	P9	{Q:process:va-albemarle-17-211-compiled}
{Q:process:va-albemarle-17-211-compiled}	P10	{Q:step:va-albemarle-17-211-compiled:transcribe_done}
{Q:step:va-albemarle-17-211-compiled:transcribe_done}	{P:bpmn_element}	"transcribe_done"
{Q:step:va-albemarle-17-211-compiled:transcribe_done}	{P:performed_by}	{Q:actor:va-albemarle-17-211-compiled:county}
{Q:step:va-albemarle-17-211-compiled:start}	P12	{Q:step:va-albemarle-17-211-compiled:file_request_wait}
{Q:step:va-albemarle-17-211-compiled:file_request_wait}	P11	{Q:step:va-albemarle-17-211-compiled:start}
{Q:step:va-albemarle-17-211-compiled:file_request_wait}	P12	{Q:step:va-albemarle-17-211-compiled:file_request}
{Q:step:va-albemarle-17-211-compiled:file_request}	P11	{Q:step:va-albemarle-17-211-compiled:file_request_wait}
{Q:step:va-albemarle-17-211-compiled:file_request_wait}	P12	{Q:step:va-albemarle-17-211-compiled:file_request_timeout}
{Q:step:va-albemarle-17-211-compiled:file_request_timeout}	P11	{Q:step:va-albemarle-17-211-compiled:file_request_wait}
{Q:step:va-albemarle-17-211-compiled:file_request}	P12	{Q:step:va-albemarle-17-211-compiled:determine_standing}
{Q:step:va-albemarle-17-211-compiled:determine_standing}	P11	{Q:step:va-albemarle-17-211-compiled:file_request}
{Q:step:va-albemarle-17-211-compiled:file_request_timeout}	P12	{Q:step:va-albemarle-17-211-compiled:file_request_lapsed}
{Q:step:va-albemarle-17-211-compiled:file_request_lapsed}	P11	{Q:step:va-albemarle-17-211-compiled:file_request_timeout}
{Q:step:va-albemarle-17-211-compiled:determine_standing}	P12	{Q:step:va-albemarle-17-211-compiled:determine_standing_gw}
{Q:step:va-albemarle-17-211-compiled:determine_standing_gw}	P11	{Q:step:va-albemarle-17-211-compiled:determine_standing}
{Q:step:va-albemarle-17-211-compiled:hold_hearing}	P12	{Q:step:va-albemarle-17-211-compiled:consider_evidence}
{Q:step:va-albemarle-17-211-compiled:consider_evidence}	P11	{Q:step:va-albemarle-17-211-compiled:hold_hearing}
{Q:step:va-albemarle-17-211-compiled:hold_hearing}	P12	{Q:step:va-albemarle-17-211-compiled:keep_record}
{Q:step:va-albemarle-17-211-compiled:keep_record}	P11	{Q:step:va-albemarle-17-211-compiled:hold_hearing}
{Q:step:va-albemarle-17-211-compiled:hold_hearing_deadline}	P12	{Q:step:va-albemarle-17-211-compiled:hold_hearing_deadline_end}
{Q:step:va-albemarle-17-211-compiled:hold_hearing_deadline_end}	P11	{Q:step:va-albemarle-17-211-compiled:hold_hearing_deadline}
{Q:step:va-albemarle-17-211-compiled:consider_evidence}	P12	{Q:step:va-albemarle-17-211-compiled:issue_decision}
{Q:step:va-albemarle-17-211-compiled:issue_decision}	P11	{Q:step:va-albemarle-17-211-compiled:consider_evidence}
{Q:step:va-albemarle-17-211-compiled:keep_record}	P12	{Q:step:va-albemarle-17-211-compiled:issue_decision}
{Q:step:va-albemarle-17-211-compiled:issue_decision}	P11	{Q:step:va-albemarle-17-211-compiled:keep_record}
{Q:step:va-albemarle-17-211-compiled:issue_decision}	P12	{Q:step:va-albemarle-17-211-compiled:appeal_to_court_wait}
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_wait}	P11	{Q:step:va-albemarle-17-211-compiled:issue_decision}
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_wait}	P12	{Q:step:va-albemarle-17-211-compiled:appeal_to_court}
{Q:step:va-albemarle-17-211-compiled:appeal_to_court}	P11	{Q:step:va-albemarle-17-211-compiled:appeal_to_court_wait}
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_wait}	P12	{Q:step:va-albemarle-17-211-compiled:appeal_to_court_timeout}
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_timeout}	P11	{Q:step:va-albemarle-17-211-compiled:appeal_to_court_wait}
{Q:step:va-albemarle-17-211-compiled:appeal_to_court}	P12	{Q:step:va-albemarle-17-211-compiled:transcribe}
{Q:step:va-albemarle-17-211-compiled:transcribe}	P11	{Q:step:va-albemarle-17-211-compiled:appeal_to_court}
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_timeout}	P12	{Q:step:va-albemarle-17-211-compiled:appeal_to_court_lapsed}
{Q:step:va-albemarle-17-211-compiled:appeal_to_court_lapsed}	P11	{Q:step:va-albemarle-17-211-compiled:appeal_to_court_timeout}
{Q:step:va-albemarle-17-211-compiled:transcribe}	P12	{Q:step:va-albemarle-17-211-compiled:transcribe_done}
{Q:step:va-albemarle-17-211-compiled:transcribe_done}	P11	{Q:step:va-albemarle-17-211-compiled:transcribe}
{Q:step:va-albemarle-17-211-compiled:determine_standing_gw}	P12	{Q:step:va-albemarle-17-211-compiled:determine_standing_not_hold_hearing}
{Q:step:va-albemarle-17-211-compiled:determine_standing_not_hold_hearing}	P11	{Q:step:va-albemarle-17-211-compiled:determine_standing_gw}
{Q:step:va-albemarle-17-211-compiled:determine_standing_gw}	P12	{Q:step:va-albemarle-17-211-compiled:hold_hearing}
{Q:step:va-albemarle-17-211-compiled:hold_hearing}	P11	{Q:step:va-albemarle-17-211-compiled:determine_standing_gw}
