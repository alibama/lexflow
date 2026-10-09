{Q:jurisdiction:va/albemarle_county}	P8	"https://www.wikidata.org/wiki/Q488653"
{Q:process:va-albemarle-17-211}	P5	Q7
{Q:process:va-albemarle-17-211}	P15	{Q:jurisdiction:va/albemarle_county}
{Q:process:va-albemarle-17-211}	{P:wiki_page}	"https://lexipedia.xyz/doku.php?id=process:va:albemarle_county:17-211"
{Q:process:va-albemarle-17-211}	{P:bpmn_model}	"https://lexipedia.xyz/lib/exe/fetch.php?media=process:va:albemarle_county:17-211.bpmn"
{Q:process:va-albemarle-17-211}	{P:dmn_model}	"https://lexipedia.xyz/lib/exe/fetch.php?media=process:va:albemarle_county:17-211.dmn"
{Q:provision:va/albemarle_county:17-211}	P5	Q10
{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211"
{Q:provision:va/albemarle_county:17-211}	P25	"17-211"
{Q:provision:va/albemarle_county:17-211}	P23	"https://library.municode.com/va/albemarle_county/codes/code_of_ordinances"
{Q:provision:va/albemarle_county:17-211}	{P:wiki_page}	"https://lexipedia.xyz/doku.php?id=law:va:albemarle_county:17-211"
{Q:provision:va/albemarle_county:17-211}	P15	{Q:jurisdiction:va/albemarle_county}
{Q:provision:va/albemarle_county:17-211}	P24	+2014-07-01T00:00:00Z/11	P25	"Ord. 14-17(1)"
{Q:process:va-albemarle-17-211}	P13	{Q:provision:va/albemarle_county:17-211}
{Q:provision:va:62.1-44.15:46}	P5	Q10
{Q:provision:va:62.1-44.15:46}	P22	"Code of Virginia § 62.1-44.15:46"
{Q:provision:va:62.1-44.15:46}	P25	"62.1-44.15:46"
{Q:provision:va:62.1-44.15:46}	P23	"https://law.lis.virginia.gov/vacode/62.1-44.15:46/"
{Q:provision:va:62.1-44.15:46}	{P:wiki_page}	"https://lexipedia.xyz/doku.php?id=law:va:62.1-44.15_46"
{Q:process:va-albemarle-17-211}	P13	{Q:provision:va:62.1-44.15:46}
{Q:actor:va-albemarle-17-211:county}	P8	"https://www.wikidata.org/wiki/Q488653"
{Q:step:va-albemarle-17-211:a_start}	P5	Q8
{Q:step:va-albemarle-17-211:a_start}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:a_start}
{Q:step:va-albemarle-17-211:a_start}	{P:bpmn_element}	"a_start"
{Q:step:va-albemarle-17-211:a_start}	{P:performed_by}	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_start}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:a_decide}	P5	Q8
{Q:step:va-albemarle-17-211:a_decide}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:a_decide}
{Q:step:va-albemarle-17-211:a_decide}	{P:bpmn_element}	"a_decide"
{Q:step:va-albemarle-17-211:a_decide}	{P:performed_by}	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_decide}	P16	Q14	P17	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_decide}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:a_window}	P5	Q8
{Q:step:va-albemarle-17-211:a_window}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:a_window}
{Q:step:va-albemarle-17-211:a_window}	{P:bpmn_element}	"a_window"
{Q:step:va-albemarle-17-211:a_window}	{P:performed_by}	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_window}	{P:time_limit}	"P30D"	{P:deadline_anchor}	"notice date / required-action date / approval date"
{Q:step:va-albemarle-17-211:a_window}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)(1)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:a_window}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)(2)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:a_window}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)(3)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:a_lapsed}	P5	Q8
{Q:step:va-albemarle-17-211:a_lapsed}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:a_lapsed}
{Q:step:va-albemarle-17-211:a_lapsed}	{P:bpmn_element}	"a_lapsed"
{Q:step:va-albemarle-17-211:a_lapsed}	{P:performed_by}	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_lapsed}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)"	{P:grounding}	"implied"
{Q:step:va-albemarle-17-211:a_gw}	P5	Q9
{Q:step:va-albemarle-17-211:a_gw}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:a_gw}
{Q:step:va-albemarle-17-211:a_gw}	{P:bpmn_element}	"a_gw"
{Q:step:va-albemarle-17-211:a_gw}	{P:performed_by}	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_no}	P5	Q8
{Q:step:va-albemarle-17-211:a_no}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:a_no}
{Q:step:va-albemarle-17-211:a_no}	{P:bpmn_element}	"a_no"
{Q:step:va-albemarle-17-211:a_no}	{P:performed_by}	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_file}	P5	Q8
{Q:step:va-albemarle-17-211:a_file}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:a_file}
{Q:step:va-albemarle-17-211:a_file}	{P:bpmn_element}	"a_file"
{Q:step:va-albemarle-17-211:a_file}	{P:performed_by}	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_file}	P16	Q14	P17	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_file}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:a_file}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:a_wait}	P5	Q8
{Q:step:va-albemarle-17-211:a_wait}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:a_wait}
{Q:step:va-albemarle-17-211:a_wait}	{P:bpmn_element}	"a_wait"
{Q:step:va-albemarle-17-211:a_wait}	{P:performed_by}	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_wait}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(F)"	{P:grounding}	"implied"
{Q:step:va-albemarle-17-211:a_decide_jr}	P5	Q8
{Q:step:va-albemarle-17-211:a_decide_jr}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:a_decide_jr}
{Q:step:va-albemarle-17-211:a_decide_jr}	{P:bpmn_element}	"a_decide_jr"
{Q:step:va-albemarle-17-211:a_decide_jr}	{P:performed_by}	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_decide_jr}	P16	Q16	P17	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_decide_jr}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(F)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:a_jr_window}	P5	Q8
{Q:step:va-albemarle-17-211:a_jr_window}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:a_jr_window}
{Q:step:va-albemarle-17-211:a_jr_window}	{P:bpmn_element}	"a_jr_window"
{Q:step:va-albemarle-17-211:a_jr_window}	{P:performed_by}	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_jr_window}	{P:time_limit}	"P30D"	{P:deadline_anchor}	"date of the hearing officer's written decision"
{Q:step:va-albemarle-17-211:a_jr_window}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(F)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:a_jr_window}	P13	{Q:provision:va:62.1-44.15:46}	P22	"Va. Code § 62.1-44.15:46"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:a_time_barred}	P5	Q8
{Q:step:va-albemarle-17-211:a_time_barred}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:a_time_barred}
{Q:step:va-albemarle-17-211:a_time_barred}	{P:bpmn_element}	"a_time_barred"
{Q:step:va-albemarle-17-211:a_time_barred}	{P:performed_by}	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_time_barred}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(F)"	{P:grounding}	"implied"
{Q:step:va-albemarle-17-211:a_gw2}	P5	Q9
{Q:step:va-albemarle-17-211:a_gw2}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:a_gw2}
{Q:step:va-albemarle-17-211:a_gw2}	{P:bpmn_element}	"a_gw2"
{Q:step:va-albemarle-17-211:a_gw2}	{P:performed_by}	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_accept}	P5	Q8
{Q:step:va-albemarle-17-211:a_accept}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:a_accept}
{Q:step:va-albemarle-17-211:a_accept}	{P:bpmn_element}	"a_accept"
{Q:step:va-albemarle-17-211:a_accept}	{P:performed_by}	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_appeal}	P5	Q8
{Q:step:va-albemarle-17-211:a_appeal}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:a_appeal}
{Q:step:va-albemarle-17-211:a_appeal}	{P:bpmn_element}	"a_appeal"
{Q:step:va-albemarle-17-211:a_appeal}	{P:performed_by}	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_appeal}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(F)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:a_notify}	P5	Q8
{Q:step:va-albemarle-17-211:a_notify}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:a_notify}
{Q:step:va-albemarle-17-211:a_notify}	{P:bpmn_element}	"a_notify"
{Q:step:va-albemarle-17-211:a_notify}	{P:performed_by}	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_notify}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(4)"	{P:grounding}	"assumed"
{Q:step:va-albemarle-17-211:a_jr}	P5	Q8
{Q:step:va-albemarle-17-211:a_jr}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:a_jr}
{Q:step:va-albemarle-17-211:a_jr}	{P:bpmn_element}	"a_jr"
{Q:step:va-albemarle-17-211:a_jr}	{P:performed_by}	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:a_jr}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(F)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:a_jr}	P13	{Q:provision:va:62.1-44.15:46}	P22	"Va. Code § 62.1-44.15:46"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:a_end}	P5	Q8
{Q:step:va-albemarle-17-211:a_end}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:a_end}
{Q:step:va-albemarle-17-211:a_end}	{P:bpmn_element}	"a_end"
{Q:step:va-albemarle-17-211:a_end}	{P:performed_by}	{Q:actor:va-albemarle-17-211:appellant}
{Q:step:va-albemarle-17-211:c_start}	P5	Q8
{Q:step:va-albemarle-17-211:c_start}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_start}
{Q:step:va-albemarle-17-211:c_start}	{P:bpmn_element}	"c_start"
{Q:step:va-albemarle-17-211:c_start}	{P:performed_by}	{Q:actor:va-albemarle-17-211:administrator}
{Q:step:va-albemarle-17-211:c_start}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(A)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:c_notify}	P5	Q8
{Q:step:va-albemarle-17-211:c_notify}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_notify}
{Q:step:va-albemarle-17-211:c_notify}	{P:bpmn_element}	"c_notify"
{Q:step:va-albemarle-17-211:c_notify}	{P:performed_by}	{Q:actor:va-albemarle-17-211:administrator}
{Q:step:va-albemarle-17-211:c_notify}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)(1)"	{P:grounding}	"implied"
{Q:step:va-albemarle-17-211:c_await_request}	P5	Q9
{Q:step:va-albemarle-17-211:c_await_request}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_await_request}
{Q:step:va-albemarle-17-211:c_await_request}	{P:bpmn_element}	"c_await_request"
{Q:step:va-albemarle-17-211:c_await_request}	{P:performed_by}	{Q:actor:va-albemarle-17-211:clerk}
{Q:step:va-albemarle-17-211:c_request}	P5	Q8
{Q:step:va-albemarle-17-211:c_request}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_request}
{Q:step:va-albemarle-17-211:c_request}	{P:bpmn_element}	"c_request"
{Q:step:va-albemarle-17-211:c_request}	{P:performed_by}	{Q:actor:va-albemarle-17-211:clerk}
{Q:step:va-albemarle-17-211:c_request}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:c_window}	P5	Q8
{Q:step:va-albemarle-17-211:c_window}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_window}
{Q:step:va-albemarle-17-211:c_window}	{P:bpmn_element}	"c_window"
{Q:step:va-albemarle-17-211:c_window}	{P:performed_by}	{Q:actor:va-albemarle-17-211:clerk}
{Q:step:va-albemarle-17-211:c_window}	{P:time_limit}	"P30D"	{P:deadline_anchor}	"notice date / required-action date / approval date"
{Q:step:va-albemarle-17-211:c_window}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)(1)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:c_window}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)(2)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:c_window}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)(3)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:c_lapsed}	P5	Q8
{Q:step:va-albemarle-17-211:c_lapsed}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_lapsed}
{Q:step:va-albemarle-17-211:c_lapsed}	{P:bpmn_element}	"c_lapsed"
{Q:step:va-albemarle-17-211:c_lapsed}	{P:performed_by}	{Q:actor:va-albemarle-17-211:clerk}
{Q:step:va-albemarle-17-211:c_lapsed}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)"	{P:grounding}	"implied"
{Q:step:va-albemarle-17-211:c_grounds_gw}	P5	Q9
{Q:step:va-albemarle-17-211:c_grounds_gw}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_grounds_gw}
{Q:step:va-albemarle-17-211:c_grounds_gw}	{P:bpmn_element}	"c_grounds_gw"
{Q:step:va-albemarle-17-211:c_grounds_gw}	{P:performed_by}	{Q:actor:va-albemarle-17-211:clerk}
{Q:step:va-albemarle-17-211:c_grounds_gw}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:c_await_grounds}	P5	Q8
{Q:step:va-albemarle-17-211:c_await_grounds}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_await_grounds}
{Q:step:va-albemarle-17-211:c_await_grounds}	{P:bpmn_element}	"c_await_grounds"
{Q:step:va-albemarle-17-211:c_await_grounds}	{P:performed_by}	{Q:actor:va-albemarle-17-211:clerk}
{Q:step:va-albemarle-17-211:c_await_grounds}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(C)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:c_review_rules}	P5	Q9
{Q:step:va-albemarle-17-211:c_review_rules}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_review_rules}
{Q:step:va-albemarle-17-211:c_review_rules}	{P:bpmn_element}	"c_review_rules"
{Q:step:va-albemarle-17-211:c_review_rules}	{P:performed_by}	{Q:actor:va-albemarle-17-211:hearing_officer}
{Q:step:va-albemarle-17-211:c_review_rules}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(A)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:c_review_rules}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(B)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:c_standing_gw}	P5	Q9
{Q:step:va-albemarle-17-211:c_standing_gw}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_standing_gw}
{Q:step:va-albemarle-17-211:c_standing_gw}	{P:bpmn_element}	"c_standing_gw"
{Q:step:va-albemarle-17-211:c_standing_gw}	{P:performed_by}	{Q:actor:va-albemarle-17-211:hearing_officer}
{Q:step:va-albemarle-17-211:c_dismiss}	P5	Q8
{Q:step:va-albemarle-17-211:c_dismiss}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_dismiss}
{Q:step:va-albemarle-17-211:c_dismiss}	{P:bpmn_element}	"c_dismiss"
{Q:step:va-albemarle-17-211:c_dismiss}	{P:performed_by}	{Q:actor:va-albemarle-17-211:hearing_officer}
{Q:step:va-albemarle-17-211:c_dismiss}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(B)"	{P:grounding}	"implied"
{Q:step:va-albemarle-17-211:c_phase}	P5	Q8
{Q:step:va-albemarle-17-211:c_phase}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_phase}
{Q:step:va-albemarle-17-211:c_phase}	{P:bpmn_element}	"c_phase"
{Q:step:va-albemarle-17-211:c_phase}	{P:performed_by}	{Q:actor:va-albemarle-17-211:hearing_officer}
{Q:step:va-albemarle-17-211:c_phase}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(2)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:ph_start}	P5	Q8
{Q:step:va-albemarle-17-211:ph_start}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:ph_start}
{Q:step:va-albemarle-17-211:ph_start}	{P:bpmn_element}	"ph_start"
{Q:step:va-albemarle-17-211:ph_start}	{P:performed_by}	{Q:actor:va-albemarle-17-211:county}
{Q:step:va-albemarle-17-211:ph_schedule}	P5	Q8
{Q:step:va-albemarle-17-211:ph_schedule}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:ph_schedule}
{Q:step:va-albemarle-17-211:ph_schedule}	{P:bpmn_element}	"ph_schedule"
{Q:step:va-albemarle-17-211:ph_schedule}	{P:performed_by}	{Q:actor:va-albemarle-17-211:hearing_officer}
{Q:step:va-albemarle-17-211:ph_schedule}	P16	Q13	P17	{Q:actor:va-albemarle-17-211:hearing_officer}
{Q:step:va-albemarle-17-211:ph_schedule}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(2)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:ph_ext}	P5	Q8
{Q:step:va-albemarle-17-211:ph_ext}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:ph_ext}
{Q:step:va-albemarle-17-211:ph_ext}	{P:bpmn_element}	"ph_ext"
{Q:step:va-albemarle-17-211:ph_ext}	{P:performed_by}	{Q:actor:va-albemarle-17-211:county}
{Q:step:va-albemarle-17-211:ph_ext}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(2)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:ph_extend}	P5	Q8
{Q:step:va-albemarle-17-211:ph_extend}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:ph_extend}
{Q:step:va-albemarle-17-211:ph_extend}	{P:bpmn_element}	"ph_extend"
{Q:step:va-albemarle-17-211:ph_extend}	{P:performed_by}	{Q:actor:va-albemarle-17-211:hearing_officer}
{Q:step:va-albemarle-17-211:ph_extend}	P16	Q14	P17	{Q:actor:va-albemarle-17-211:hearing_officer}
{Q:step:va-albemarle-17-211:ph_extend}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(2)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:ph_ext_end}	P5	Q8
{Q:step:va-albemarle-17-211:ph_ext_end}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:ph_ext_end}
{Q:step:va-albemarle-17-211:ph_ext_end}	{P:bpmn_element}	"ph_ext_end"
{Q:step:va-albemarle-17-211:ph_ext_end}	{P:performed_by}	{Q:actor:va-albemarle-17-211:county}
{Q:step:va-albemarle-17-211:ph_hearing}	P5	Q8
{Q:step:va-albemarle-17-211:ph_hearing}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:ph_hearing}
{Q:step:va-albemarle-17-211:ph_hearing}	{P:bpmn_element}	"ph_hearing"
{Q:step:va-albemarle-17-211:ph_hearing}	{P:performed_by}	{Q:actor:va-albemarle-17-211:county}
{Q:step:va-albemarle-17-211:ph_hearing}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(1)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:h_start}	P5	Q8
{Q:step:va-albemarle-17-211:h_start}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:h_start}
{Q:step:va-albemarle-17-211:h_start}	{P:bpmn_element}	"h_start"
{Q:step:va-albemarle-17-211:h_start}	{P:performed_by}	{Q:actor:va-albemarle-17-211:county}
{Q:step:va-albemarle-17-211:h_evidence}	P5	Q8
{Q:step:va-albemarle-17-211:h_evidence}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:h_evidence}
{Q:step:va-albemarle-17-211:h_evidence}	{P:bpmn_element}	"h_evidence"
{Q:step:va-albemarle-17-211:h_evidence}	{P:performed_by}	{Q:actor:va-albemarle-17-211:county}
{Q:step:va-albemarle-17-211:h_evidence}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(3)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:h_consider}	P5	Q8
{Q:step:va-albemarle-17-211:h_consider}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:h_consider}
{Q:step:va-albemarle-17-211:h_consider}	{P:bpmn_element}	"h_consider"
{Q:step:va-albemarle-17-211:h_consider}	{P:performed_by}	{Q:actor:va-albemarle-17-211:hearing_officer}
{Q:step:va-albemarle-17-211:h_consider}	P16	Q13	P17	{Q:actor:va-albemarle-17-211:hearing_officer}
{Q:step:va-albemarle-17-211:h_consider}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(3)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:h_record}	P5	Q8
{Q:step:va-albemarle-17-211:h_record}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:h_record}
{Q:step:va-albemarle-17-211:h_record}	{P:bpmn_element}	"h_record"
{Q:step:va-albemarle-17-211:h_record}	{P:performed_by}	{Q:actor:va-albemarle-17-211:county}
{Q:step:va-albemarle-17-211:h_record}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(4)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:h_end}	P5	Q8
{Q:step:va-albemarle-17-211:h_end}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:h_end}
{Q:step:va-albemarle-17-211:h_end}	{P:bpmn_element}	"h_end"
{Q:step:va-albemarle-17-211:h_end}	{P:performed_by}	{Q:actor:va-albemarle-17-211:county}
{Q:step:va-albemarle-17-211:ph_end}	P5	Q8
{Q:step:va-albemarle-17-211:ph_end}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:ph_end}
{Q:step:va-albemarle-17-211:ph_end}	{P:bpmn_element}	"ph_end"
{Q:step:va-albemarle-17-211:ph_end}	{P:performed_by}	{Q:actor:va-albemarle-17-211:county}
{Q:step:va-albemarle-17-211:c_target}	P5	Q8
{Q:step:va-albemarle-17-211:c_target}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_target}
{Q:step:va-albemarle-17-211:c_target}	{P:bpmn_element}	"c_target"
{Q:step:va-albemarle-17-211:c_target}	{P:performed_by}	{Q:actor:va-albemarle-17-211:county}
{Q:step:va-albemarle-17-211:c_target}	{P:time_limit}	"P30D"	{P:deadline_anchor}	"receipt of the petition (clock starts once grounds are stated)"
{Q:step:va-albemarle-17-211:c_target}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(2)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:c_target_end}	P5	Q8
{Q:step:va-albemarle-17-211:c_target_end}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_target_end}
{Q:step:va-albemarle-17-211:c_target_end}	{P:bpmn_element}	"c_target_end"
{Q:step:va-albemarle-17-211:c_target_end}	{P:performed_by}	{Q:actor:va-albemarle-17-211:hearing_officer}
{Q:step:va-albemarle-17-211:c_target_end}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(2)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:c_decide}	P5	Q8
{Q:step:va-albemarle-17-211:c_decide}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_decide}
{Q:step:va-albemarle-17-211:c_decide}	{P:bpmn_element}	"c_decide"
{Q:step:va-albemarle-17-211:c_decide}	{P:performed_by}	{Q:actor:va-albemarle-17-211:hearing_officer}
{Q:step:va-albemarle-17-211:c_decide}	P16	Q13	P17	{Q:actor:va-albemarle-17-211:hearing_officer}
{Q:step:va-albemarle-17-211:c_decide}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(F)"	{P:grounding}	"implied"
{Q:step:va-albemarle-17-211:c_after_gw}	P5	Q9
{Q:step:va-albemarle-17-211:c_after_gw}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_after_gw}
{Q:step:va-albemarle-17-211:c_after_gw}	{P:bpmn_element}	"c_after_gw"
{Q:step:va-albemarle-17-211:c_after_gw}	{P:performed_by}	{Q:actor:va-albemarle-17-211:clerk}
{Q:step:va-albemarle-17-211:c_jr_notice}	P5	Q8
{Q:step:va-albemarle-17-211:c_jr_notice}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_jr_notice}
{Q:step:va-albemarle-17-211:c_jr_notice}	{P:bpmn_element}	"c_jr_notice"
{Q:step:va-albemarle-17-211:c_jr_notice}	{P:performed_by}	{Q:actor:va-albemarle-17-211:clerk}
{Q:step:va-albemarle-17-211:c_jr_notice}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(4)"	{P:grounding}	"implied"
{Q:step:va-albemarle-17-211:c_transcribe}	P5	Q8
{Q:step:va-albemarle-17-211:c_transcribe}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_transcribe}
{Q:step:va-albemarle-17-211:c_transcribe}	{P:bpmn_element}	"c_transcribe"
{Q:step:va-albemarle-17-211:c_transcribe}	{P:performed_by}	{Q:actor:va-albemarle-17-211:clerk}
{Q:step:va-albemarle-17-211:c_transcribe}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(D)(4)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:c_transmit}	P5	Q8
{Q:step:va-albemarle-17-211:c_transmit}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_transmit}
{Q:step:va-albemarle-17-211:c_transmit}	{P:bpmn_element}	"c_transmit"
{Q:step:va-albemarle-17-211:c_transmit}	{P:performed_by}	{Q:actor:va-albemarle-17-211:clerk}
{Q:step:va-albemarle-17-211:c_transmit}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(F)"	{P:grounding}	"assumed"
{Q:step:va-albemarle-17-211:c_jr_end}	P5	Q8
{Q:step:va-albemarle-17-211:c_jr_end}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_jr_end}
{Q:step:va-albemarle-17-211:c_jr_end}	{P:bpmn_element}	"c_jr_end"
{Q:step:va-albemarle-17-211:c_jr_end}	{P:performed_by}	{Q:actor:va-albemarle-17-211:clerk}
{Q:step:va-albemarle-17-211:c_jr_window}	P5	Q8
{Q:step:va-albemarle-17-211:c_jr_window}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_jr_window}
{Q:step:va-albemarle-17-211:c_jr_window}	{P:bpmn_element}	"c_jr_window"
{Q:step:va-albemarle-17-211:c_jr_window}	{P:performed_by}	{Q:actor:va-albemarle-17-211:clerk}
{Q:step:va-albemarle-17-211:c_jr_window}	{P:time_limit}	"P30D"	{P:deadline_anchor}	"date of the hearing officer's written decision"
{Q:step:va-albemarle-17-211:c_jr_window}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(F)"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:c_jr_window}	P13	{Q:provision:va:62.1-44.15:46}	P22	"Va. Code § 62.1-44.15:46"	{P:grounding}	"explicit"
{Q:step:va-albemarle-17-211:c_final}	P5	Q8
{Q:step:va-albemarle-17-211:c_final}	P9	{Q:process:va-albemarle-17-211}
{Q:process:va-albemarle-17-211}	P10	{Q:step:va-albemarle-17-211:c_final}
{Q:step:va-albemarle-17-211:c_final}	{P:bpmn_element}	"c_final"
{Q:step:va-albemarle-17-211:c_final}	{P:performed_by}	{Q:actor:va-albemarle-17-211:clerk}
{Q:step:va-albemarle-17-211:c_final}	P13	{Q:provision:va/albemarle_county:17-211}	P22	"Albemarle County Code § 17-211(F)"	{P:grounding}	"implied"
{Q:step:va-albemarle-17-211:a_start}	P12	{Q:step:va-albemarle-17-211:a_decide}
{Q:step:va-albemarle-17-211:a_decide}	P11	{Q:step:va-albemarle-17-211:a_start}
{Q:step:va-albemarle-17-211:a_decide}	P12	{Q:step:va-albemarle-17-211:a_gw}
{Q:step:va-albemarle-17-211:a_gw}	P11	{Q:step:va-albemarle-17-211:a_decide}
{Q:step:va-albemarle-17-211:a_window}	P12	{Q:step:va-albemarle-17-211:a_lapsed}
{Q:step:va-albemarle-17-211:a_lapsed}	P11	{Q:step:va-albemarle-17-211:a_window}
{Q:step:va-albemarle-17-211:a_gw}	P12	{Q:step:va-albemarle-17-211:a_file}
{Q:step:va-albemarle-17-211:a_file}	P11	{Q:step:va-albemarle-17-211:a_gw}
{Q:step:va-albemarle-17-211:a_gw}	P12	{Q:step:va-albemarle-17-211:a_no}
{Q:step:va-albemarle-17-211:a_no}	P11	{Q:step:va-albemarle-17-211:a_gw}
{Q:step:va-albemarle-17-211:a_file}	P12	{Q:step:va-albemarle-17-211:a_wait}
{Q:step:va-albemarle-17-211:a_wait}	P11	{Q:step:va-albemarle-17-211:a_file}
{Q:step:va-albemarle-17-211:a_wait}	P12	{Q:step:va-albemarle-17-211:a_decide_jr}
{Q:step:va-albemarle-17-211:a_decide_jr}	P11	{Q:step:va-albemarle-17-211:a_wait}
{Q:step:va-albemarle-17-211:a_decide_jr}	P12	{Q:step:va-albemarle-17-211:a_gw2}
{Q:step:va-albemarle-17-211:a_gw2}	P11	{Q:step:va-albemarle-17-211:a_decide_jr}
{Q:step:va-albemarle-17-211:a_jr_window}	P12	{Q:step:va-albemarle-17-211:a_time_barred}
{Q:step:va-albemarle-17-211:a_time_barred}	P11	{Q:step:va-albemarle-17-211:a_jr_window}
{Q:step:va-albemarle-17-211:a_gw2}	P12	{Q:step:va-albemarle-17-211:a_accept}
{Q:step:va-albemarle-17-211:a_accept}	P11	{Q:step:va-albemarle-17-211:a_gw2}
{Q:step:va-albemarle-17-211:a_gw2}	P12	{Q:step:va-albemarle-17-211:a_appeal}
{Q:step:va-albemarle-17-211:a_appeal}	P11	{Q:step:va-albemarle-17-211:a_gw2}
{Q:step:va-albemarle-17-211:a_appeal}	P12	{Q:step:va-albemarle-17-211:a_notify}
{Q:step:va-albemarle-17-211:a_notify}	P11	{Q:step:va-albemarle-17-211:a_appeal}
{Q:step:va-albemarle-17-211:a_notify}	P12	{Q:step:va-albemarle-17-211:a_jr}
{Q:step:va-albemarle-17-211:a_jr}	P11	{Q:step:va-albemarle-17-211:a_notify}
{Q:step:va-albemarle-17-211:a_jr}	P12	{Q:step:va-albemarle-17-211:a_end}
{Q:step:va-albemarle-17-211:a_end}	P11	{Q:step:va-albemarle-17-211:a_jr}
{Q:step:va-albemarle-17-211:c_start}	P12	{Q:step:va-albemarle-17-211:c_notify}
{Q:step:va-albemarle-17-211:c_notify}	P11	{Q:step:va-albemarle-17-211:c_start}
{Q:step:va-albemarle-17-211:c_notify}	P12	{Q:step:va-albemarle-17-211:c_await_request}
{Q:step:va-albemarle-17-211:c_await_request}	P11	{Q:step:va-albemarle-17-211:c_notify}
{Q:step:va-albemarle-17-211:c_await_request}	P12	{Q:step:va-albemarle-17-211:c_request}
{Q:step:va-albemarle-17-211:c_request}	P11	{Q:step:va-albemarle-17-211:c_await_request}
{Q:step:va-albemarle-17-211:c_await_request}	P12	{Q:step:va-albemarle-17-211:c_window}
{Q:step:va-albemarle-17-211:c_window}	P11	{Q:step:va-albemarle-17-211:c_await_request}
{Q:step:va-albemarle-17-211:c_request}	P12	{Q:step:va-albemarle-17-211:c_grounds_gw}
{Q:step:va-albemarle-17-211:c_grounds_gw}	P11	{Q:step:va-albemarle-17-211:c_request}
{Q:step:va-albemarle-17-211:c_window}	P12	{Q:step:va-albemarle-17-211:c_lapsed}
{Q:step:va-albemarle-17-211:c_lapsed}	P11	{Q:step:va-albemarle-17-211:c_window}
{Q:step:va-albemarle-17-211:c_grounds_gw}	P12	{Q:step:va-albemarle-17-211:c_await_grounds}
{Q:step:va-albemarle-17-211:c_await_grounds}	P11	{Q:step:va-albemarle-17-211:c_grounds_gw}
{Q:step:va-albemarle-17-211:c_grounds_gw}	P12	{Q:step:va-albemarle-17-211:c_review_rules}
{Q:step:va-albemarle-17-211:c_review_rules}	P11	{Q:step:va-albemarle-17-211:c_grounds_gw}
{Q:step:va-albemarle-17-211:c_await_grounds}	P12	{Q:step:va-albemarle-17-211:c_review_rules}
{Q:step:va-albemarle-17-211:c_review_rules}	P11	{Q:step:va-albemarle-17-211:c_await_grounds}
{Q:step:va-albemarle-17-211:c_review_rules}	P12	{Q:step:va-albemarle-17-211:c_standing_gw}
{Q:step:va-albemarle-17-211:c_standing_gw}	P11	{Q:step:va-albemarle-17-211:c_review_rules}
{Q:step:va-albemarle-17-211:c_standing_gw}	P12	{Q:step:va-albemarle-17-211:c_dismiss}
{Q:step:va-albemarle-17-211:c_dismiss}	P11	{Q:step:va-albemarle-17-211:c_standing_gw}
{Q:step:va-albemarle-17-211:c_standing_gw}	P12	{Q:step:va-albemarle-17-211:c_phase}
{Q:step:va-albemarle-17-211:c_phase}	P11	{Q:step:va-albemarle-17-211:c_standing_gw}
{Q:step:va-albemarle-17-211:ph_start}	P12	{Q:step:va-albemarle-17-211:ph_schedule}
{Q:step:va-albemarle-17-211:ph_schedule}	P11	{Q:step:va-albemarle-17-211:ph_start}
{Q:step:va-albemarle-17-211:ph_schedule}	P12	{Q:step:va-albemarle-17-211:ph_hearing}
{Q:step:va-albemarle-17-211:ph_hearing}	P11	{Q:step:va-albemarle-17-211:ph_schedule}
{Q:step:va-albemarle-17-211:ph_ext}	P12	{Q:step:va-albemarle-17-211:ph_extend}
{Q:step:va-albemarle-17-211:ph_extend}	P11	{Q:step:va-albemarle-17-211:ph_ext}
{Q:step:va-albemarle-17-211:ph_extend}	P12	{Q:step:va-albemarle-17-211:ph_ext_end}
{Q:step:va-albemarle-17-211:ph_ext_end}	P11	{Q:step:va-albemarle-17-211:ph_extend}
{Q:step:va-albemarle-17-211:h_start}	P12	{Q:step:va-albemarle-17-211:h_evidence}
{Q:step:va-albemarle-17-211:h_evidence}	P11	{Q:step:va-albemarle-17-211:h_start}
{Q:step:va-albemarle-17-211:h_evidence}	P12	{Q:step:va-albemarle-17-211:h_consider}
{Q:step:va-albemarle-17-211:h_consider}	P11	{Q:step:va-albemarle-17-211:h_evidence}
{Q:step:va-albemarle-17-211:h_consider}	P12	{Q:step:va-albemarle-17-211:h_record}
{Q:step:va-albemarle-17-211:h_record}	P11	{Q:step:va-albemarle-17-211:h_consider}
{Q:step:va-albemarle-17-211:h_record}	P12	{Q:step:va-albemarle-17-211:h_end}
{Q:step:va-albemarle-17-211:h_end}	P11	{Q:step:va-albemarle-17-211:h_record}
{Q:step:va-albemarle-17-211:ph_hearing}	P12	{Q:step:va-albemarle-17-211:ph_end}
{Q:step:va-albemarle-17-211:ph_end}	P11	{Q:step:va-albemarle-17-211:ph_hearing}
{Q:step:va-albemarle-17-211:c_phase}	P12	{Q:step:va-albemarle-17-211:c_decide}
{Q:step:va-albemarle-17-211:c_decide}	P11	{Q:step:va-albemarle-17-211:c_phase}
{Q:step:va-albemarle-17-211:c_target}	P12	{Q:step:va-albemarle-17-211:c_target_end}
{Q:step:va-albemarle-17-211:c_target_end}	P11	{Q:step:va-albemarle-17-211:c_target}
{Q:step:va-albemarle-17-211:c_decide}	P12	{Q:step:va-albemarle-17-211:c_after_gw}
{Q:step:va-albemarle-17-211:c_after_gw}	P11	{Q:step:va-albemarle-17-211:c_decide}
{Q:step:va-albemarle-17-211:c_after_gw}	P12	{Q:step:va-albemarle-17-211:c_jr_notice}
{Q:step:va-albemarle-17-211:c_jr_notice}	P11	{Q:step:va-albemarle-17-211:c_after_gw}
{Q:step:va-albemarle-17-211:c_after_gw}	P12	{Q:step:va-albemarle-17-211:c_jr_window}
{Q:step:va-albemarle-17-211:c_jr_window}	P11	{Q:step:va-albemarle-17-211:c_after_gw}
{Q:step:va-albemarle-17-211:c_jr_notice}	P12	{Q:step:va-albemarle-17-211:c_transcribe}
{Q:step:va-albemarle-17-211:c_transcribe}	P11	{Q:step:va-albemarle-17-211:c_jr_notice}
{Q:step:va-albemarle-17-211:c_transcribe}	P12	{Q:step:va-albemarle-17-211:c_transmit}
{Q:step:va-albemarle-17-211:c_transmit}	P11	{Q:step:va-albemarle-17-211:c_transcribe}
{Q:step:va-albemarle-17-211:c_transmit}	P12	{Q:step:va-albemarle-17-211:c_jr_end}
{Q:step:va-albemarle-17-211:c_jr_end}	P11	{Q:step:va-albemarle-17-211:c_transmit}
{Q:step:va-albemarle-17-211:c_jr_window}	P12	{Q:step:va-albemarle-17-211:c_final}
{Q:step:va-albemarle-17-211:c_final}	P11	{Q:step:va-albemarle-17-211:c_jr_window}
