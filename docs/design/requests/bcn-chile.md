# Request to the Biblioteca del Congreso Nacional (Ley Chile): API key and authorisation for an index

Drafted 22 October 2026 for the operator to send **in his own words**: rewrite it, fill in the bracketed parts, and
send it yourself. Nothing has been sent. lexflow never contacts BCN on its own.

## Where to send it

The API conditions ("Condiciones de Uso de la API Ley Chile", v1.1,
https://www.bcn.cl/leychile/assets/doc/condiciones-de-uso-api-v1.1.pdf, read 22 October 2026) say that an API key
is granted on request, assessed against "los fines declarados de uso" (§3 a), through the access form, and that
notices go to "el correo electrónico registrado por el solicitante en el formulario de acceso" (§10 d). The
conditions name no e-mail address. Apply through the API access form on Ley Chile's API documentation page and
attach or paste this letter as the declared purpose; if the form has no room for it, send it through BCN's contact
form addressed to the Sección Ley Chile.

## What the conditions say (so the letter answers them)

* §1: the API exists for "fines académicos, de investigación, de innovación, de interoperabilidad o de provisión de
  servicios a la ciudadanía", and specific agreements ("convenios o acuerdos específicos") with integrating
  entities are possible.
* §3 d: permitted uses include non-profit, research and artificial-intelligence uses, within the quota.
* §3 e vi-vii: no mass, systematic or automated extraction to rebuild a database substantially equivalent to Ley
  Chile, and no mass indexing or large structured repositories beyond the declared purpose, "sin autorización
  expresa de la Biblioteca". An index of the leyes in force is exactly this, so it needs that express
  authorisation.
* §3 e viii: results must not be presented as BCN's official interpretations.
* §5 b vi: AI systems must keep traceability of the data's origin, the processing and the model's part in the
  result.
* §6: 500 requests per 24 h per key; larger quotas only for public institutions under agreement; BCN weighs the
  kind of entity (public body, university, company, NGO).
* Licence of the content: CC BY-NC-ND 4.0.

## Points to make (the substance; put them in your words)

1. Who you are and what lexflow is: an open-source project (https://github.com/alibama/lexflow) that answers
   people's questions about the law with the law's own words, and Lexipedia, its public wiki. [Your name, your
   role, any university or non-profit you act for.]
2. Commercial use: [state plainly whether any part is or will be commercial. CC BY-NC-ND and the API conditions
   depend on it; if a paid service is possible later, say so now and ask what that would require.]
3. The use: each answer quotes the article verbatim, names the norma and its version date, and links back to the
   norma on Ley Chile (`https://www.bcn.cl/leychile/navegar?idNorma=...`), with the attribution "Texto: Ley Chile,
   Biblioteca del Congreso Nacional de Chile". Texts are never altered (ND), answers are never presented as BCN's
   interpretation (§3 e viii), and every answer records the norma, its version and that a language model took
   part (§5 b vi).
4. What you ask for:
   * an API key under the standard conditions, for the current mode: at most three normas fetched per question and
     at most 100 a day, cached for a week (already how lexflow works);
   * express authorisation under §3 e vi-vii to keep an index of the **leyes in force** (about 22,000 normas;
     articles, headings and version dates, refreshed when `fechaVersion` changes), or whatever narrower scope BCN
     prefers; and the rate and hours BCN wants for the initial download (lexflow proposes one request every 2
     seconds, off-peak) or a bulk export if BCN offers one;
   * confirmation that splitting a norma into its articles for search, without changing the words, is compatible
     with the ND term of the licence.
5. Undertakings: a named contact, the user agent lexflow sends, removal of anything BCN asks to remove, and a link
   to the code that does the fetching (`lexflow/corpus/countries/chile.py`).

## Draft (Spanish)

> Asunto: Solicitud de API Key y de autorización expresa (Condiciones de Uso API Ley Chile, §3 e vi-vii)
>
> Estimados señores de la Sección Ley Chile:
>
> Mi nombre es [nombre] y [rol / institución]. Desarrollo lexflow, un proyecto de código abierto
> (https://github.com/alibama/lexflow) que responde preguntas de las personas sobre la ley citando el texto de la
> propia norma. [Indicar si existe o existirá algún uso comercial.]
>
> Quisiera incorporar la legislación chilena. Cada respuesta cita el artículo de forma literal, indica la norma y la
> fecha de su versión y enlaza a la norma en Ley Chile, con la atribución "Texto: Ley Chile, Biblioteca del Congreso
> Nacional de Chile" (CC BY-NC-ND 4.0). No modificamos los textos, no presentamos las respuestas como
> interpretaciones de la Biblioteca y registramos en cada respuesta el origen de los datos y la intervención de un
> modelo automatizado (§5 b vi).
>
> Solicito:
> 1. Una API Key en las condiciones estándar. Hoy consultamos como máximo tres normas por pregunta y cien al día, con
>    una caché de una semana.
> 2. Su autorización expresa, conforme al §3 e vi-vii, para mantener un índice de las leyes vigentes (unas 22.000
>    normas: artículos, encabezados y fechas de versión, actualizado cuando cambia la versión), o el alcance más
>    acotado que la Biblioteca estime adecuado, junto con el ritmo y el horario que prefieran para la descarga
>    inicial (proponemos una solicitud cada dos segundos, fuera de horas punta) o una exportación si la ofrecen.
> 3. Su confirmación de que dividir una norma en artículos para la búsqueda, sin alterar su texto, es compatible con
>    la cláusula SinDerivadas de la licencia.
>
> Nos comprometemos a identificarnos en cada solicitud, a retirar cualquier contenido que la Biblioteca nos indique y
> a seguir las condiciones de uso. Quedo atento a los requisitos que debamos cumplir.
>
> Atentamente,
> [nombre, correo, sitio]

## Draft (English)

> Subject: Request for an API key and express authorisation (Ley Chile API Conditions of Use, §3 e vi-vii)
>
> Dear Ley Chile team,
>
> My name is [name] and I am [role / institution]. I build lexflow, an open-source project
> (https://github.com/alibama/lexflow) that answers people's questions about the law by quoting the law itself.
> [State whether there is or will be any commercial use.]
>
> I would like to include Chilean legislation. Each answer quotes the article verbatim, names the norma and the date
> of its version, and links to the norma on Ley Chile, with the attribution "Texto: Ley Chile, Biblioteca del
> Congreso Nacional de Chile" (CC BY-NC-ND 4.0). We do not alter the texts, we do not present answers as the
> Library's interpretation, and each answer records where its data came from and that an automated model took part
> (§5 b vi).
>
> I ask for:
> 1. An API key under the standard conditions. Today we fetch at most three normas per question and one hundred a
>    day, with a one-week cache.
> 2. Your express authorisation under §3 e vi-vii to keep an index of the leyes in force (about 22,000 normas:
>    articles, headings and version dates, refreshed when the version changes), or any narrower scope the Library
>    prefers, with the rate and hours you want for the initial download (we propose one request every two seconds,
>    off-peak) or an export if you offer one.
> 3. Your confirmation that dividing a norma into its articles for search, without changing its words, is compatible
>    with the NoDerivatives term of the licence.
>
> We will identify ourselves in every request, remove anything the Library asks us to remove, and follow the
> conditions of use. I would be glad to meet any requirement you set.
>
> Yours faithfully,
> [name, e-mail, site]

## After the answer

* Key only: put it in `.env` (the variable name to be chosen when the key's use is documented; the conditions say
  the key is personal and must not be shared) and keep the interim mode (`Chile.on_demand`, limits in chile.py).
* Authorisation: record its scope, rate and date in docs/design/global-sources.md, then write the pull (the parser
  and the fixture already exist) as a resumable job like Australia's.
* Refusal: keep the interim mode only.
