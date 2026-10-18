# Nepal Disaster Research: Recent Floods, Response, and Communications

Researched Oct 17, 2026. This is the background research behind evac-ai.
Sources are linked inline. Anything marked **[unverified]** comes from memory or a single weak source. Confirm it before putting it in the pitch.

---

## 0. Summary of findings that change our plan

1. **In the floods with the least loss of life, the warning came from people upstream, not from sensors.** On Aug 26 and Oct 11, phone calls from upstream residents reached downstream towns before the official SMS did, and on Oct 11 the first wave hit Arughat (06:30) before the SMS went out (06:40). The gap is the step between a person upstream seeing the river stop and an alert reaching the right people downstream, telling them what to do.
2. **Sensors fail first.** On Aug 26, four gauges were destroyed and DHM learned of the flood from a phone call. On Oct 11, the Arughat gauge was swept away at its peak. Any system that relies only on gauges goes blind at the worst moment.
3. **Official SMS warnings were late, generic, Nepali-only, and nobody had the legal power to order an evacuation.** Residents received the same message three times, with no location, no severity, and no instruction. DHM can warn but cannot order an evacuation, and no law requires a forecast to trigger one.
4. **The Oct 11 dam was not a slowly filling lake.** A landslide or avalanche blocked the river for minutes to hours, then burst, then blocked and burst again. Our "fill a lake behind the dam" centerpiece fits the *days-long* secondary risk (for example the Aug 28 barrier lake in Tibet), not the first warning. **The usable early signal was the river suddenly stopping**, which locals noticed and which a gauge would show as a sudden *drop* in level.
5. **Our plan had a factual error: the Budhi Gandaki does have a live gauge**, at Arughat (warning 4.5 m, danger 5 m). It peaked at 8.43 m and was then swept away. The plan said there was no gauge.
6. **Some of what we planned to build already exists.** Setu Rapid (an internal app for highway incidents), the BIPAD portal (public incident, river, and rain data with an **open API**), the DHM Nepal Weather app (push alerts, trekking forecasts, offline cache), and 1155 SMS alerts targeted by area. Cell broadcast is coming but not live. See §3.
7. **There is no evidence that crowds jammed evacuation routes.** People ran uphill to the nearest high ground. The documented route failures were *bridges* (people crossing while a bridge was failing, or being cut off on the wrong bank) and *the time left to escape*. Capacity-aware splitting of people across routes may be solving a problem these floods didn't have.

---

## 1. The five most recent flood-type disasters (newest first)

### 1.1 Budhi Gandaki flash flood, Gorkha, Oct 11, 2026
Sources: [Wikipedia](https://en.wikipedia.org/wiki/2026_Budhi_Gandaki_flood), [BWSN/ADRRN SitRep 1](https://www.adrrn.net/wp-content/uploads/2026/10/Budhi_Gandaki_Flood_SitRep_1.pdf), [Kathmandu Post NDRRMA interview](https://kathmandupost.com/interviews/2026/10/11/sms-alerts-helped-avert-loss-of-life-in-budhi-gandaki-floods-says-disaster-management-chief), [Onlinekhabar: warnings from the hills](https://english.onlinekhabar.com/warnings-saved-lives-budhi-gandaki.html), [Onlinekhabar corridor](https://english.onlinekhabar.com/budhi-gandaki-corridor-flood.html), [ICIMOD](https://www.icimod.org/press-releases/landslide-dam-breach-may-have-triggered-budhi-gandaki-flash-flood/), [Trekguard log](https://trekguard.app/blog/budhi-gandaki-flash-flood-manaslu-circuit-safety-2026/)

**Before the flood**
- **The same valley flooded five weeks earlier.** On Sep 6, a 3 AM flood in the Therang Khola at Namrung (Chumnubri-4) swept away 4 houses, an iron bridge, and a suspension bridge. The district closed the Manaslu and Larke Pass trekking routes ([1](https://english.onlinekhabar.com/flood-sweeps-away-houses-gorkha.html), [2](https://english.onlinekhabar.com/gorkha-administration-urges-trekkers-to-avoid-manaslu-and-larke-pass-routes.html)).
- The flood came at the start of the autumn trekking season, when the routes had reopened: about 98 foreign tourists entered the conservation area on Oct 10. It was also the first day of Dashain, when migrant workers travel home.
- Only sporadic rain had fallen. The trigger was not rainfall.
- Cause (preliminary ICIMOD/NDRRMA/DHM assessment, Oct 14): a high-altitude **rock, ice, and permafrost avalanche** at 5,500–6,000 m between Chamar Himal and Shringi Himal fell into the Ungilung Khola and Syar Khola. It released energy equal to an M3.5 earthquake, blocked the gorge briefly, then burst. Early reports had called it a "dry landslide."

**The flood (Oct 11, NPT)**

| Time | Event |
|---|---|
| Night of Oct 10 | Suspected blockage at Chhekampar (Chumnubri-6). Locals hear rumbling and feel the ground shake. **The river stops flowing.** |
| ~03:30–03:45 | **A warning relayed by locals reaches Dharche.** The flood arrives about 15 minutes later. |
| ~04:00 | Flood enters Paiyu, Bagar, Ghattekhola, Jagat, Salleri. Hydropower staff move uphill. |
| 04:35 | Gorkha's Chief District Officer receives the first official information. |
| 05:30 | Police are told about the blockage by local hotel operators. |
| 06:20 | NDRRMA receives official information. |
| ~06:30 | **First wave reaches Arughat** (DHM). |
| 06:40 | **NDRRMA SMS goes out downstream**, about 10 minutes *after* the first wave hit Arughat. |
| 07:30 | Flood reaches Soti. The Soti iron bridge is swept away. |
| 07:50 | Second, larger wave crosses the danger level at Arughat. |
| ~08:20 | **River blocks again.** Flow at Sirdibas almost stops. |
| 08:37–09:45 | Arughat gauge reads 8.43 m (warning 4.5, danger 5). NDRRMA alerts 6 districts down to the Narayani. |
| ~10:00 | One of the three spans of the Gorkha–Dhading concrete bridge at Arughat is gone. The market is evacuated. The **gauge is swept away**. |

Reported flood heights were 20–25 m in the upper valley. Water went down, came back up, and went down again across three waves.

**Response and evacuation**
- **People evacuated themselves.** Highland residents ("lekali") phoned or ran downstream. Arughat residents woke their neighbors and fled to high ground on both banks, toward Tariphant on the Gorkha side and Salyantar on the Dhading side. Elderly people and children went first. Police followed with loudspeakers.
- An ambulance driver crossed the Arughat bridge while the flood was rising. By the time he came back, the Gorkha-side span was gone, and he carried his patient across a suspension bridge below it. **This is a documented case of a bridge failing while people were still using it.**
- Army helicopters were in the air by about 06:30–07:00. 47 people were rescued on day 1 (NDRRMA said 82, including 9 foreigners). **More than 600 had been airlifted by Oct 15.**
- 100+ foreign trekkers were stranded in Jagat, 17 in Lokpa, and 40 in Chhekampar. Trekkers above Namrung walked out over Larkya La.

**After the flood (still ongoing)**
- 0 confirmed deaths, 5 herders missing. 35–45 houses destroyed and 27 partly damaged. **At least 6 bridges lost (3 suspension, 1 Bailey, 2 motorable)**. A school and the camp of the 341 MW Budhi Gandaki hydropower project (96% complete) were swept away, and 3–4 other hydropower projects were damaged. Power is out in 3 rural municipalities.
- The lower gorge trail from Khorlabesi to Philim is closed and inbound trekking permits are frozen. The army is building temporary cliff paths and rope bridges.
- Survivors were moved to Bhumethan, where excavators are leveling terraces for shelters.
- **Duration:** the hazard itself lasted about 6 hours from the first wave until levels stabilized, with re-blocking still possible. Air-only access and trail closures are still in place on day 6.

### 1.2 Cascading September 2026 damage (Krishna Bhir, highways, Namrung, Mustang)
Sources: [Khabaree](https://english.khabaree.com/disaster/2026/09/03/krishna-bhir-landslide-blocks-prithvi-highway-after-control-structures-expire.html), [Kathmandu Post bypass](https://kathmandupost.com/national/2026/09/11/nepal-prepares-krishnabhir-bypass-as-temporary-fix-remains-uncertain), [Clickmandu](https://english.clickmandu.com/2026/09/11632/), [Nepal Views](https://english.nepalviews.com/2026/09/04/floods-and-landslides-affect-major-roads-across-country-roads-in-rasuwa-completely-blocked)

This was not one event. The August flood left damage that later monsoon rain turned into new failures.
- **Krishna Bhir (Prithvi Highway, Dhading), about Sep 1.** The Trishuli, still running high after the Aug 26 surge, eroded the road's base, and landslide-control structures built 20 years earlier had passed their design life. This blocked Kathmandu's main supply road. One-way traffic resumed about 10 days later. A 12 km road on the opposite bank was upgraded as a bypass.
- **Sep 4:** rain blocked the Prithvi, Pasang Lhamu, and Shaheed highways, and roads in Rasuwa were completely blocked.
- **Sep 6:** Namrung flood (see 1.1). **Sep 8:** an M4.9 earthquake damaged Mustang. An avalanche at Himlung base camp killed at least 4.
- **Lesson:** after a major flood, a river corridor stays dangerous for weeks, through bank erosion, damaged structures, and loose sediment. Risk does not reset after the event.

### 1.3 Bhotekoshi–Trishuli flood ("Rasuwa flood"), Aug 26, 2026
Sources: [Wikipedia](https://en.wikipedia.org/wiki/2026_Nepal%E2%80%93Tibet_floods), [Timeline](https://en.wikipedia.org/wiki/Timeline_of_the_2026_Nepal%E2%80%93Tibet_floods), [NDRRMA SitRep](https://ndrrma.gov.np/mediafiles/rasuwa/Rasuwa_Flood_SitRep_Temp_ENG_01_01092026.pdf), [Mongabay on warnings](https://news.mongabay.com/2026/09/during-nepal-floods-decentralized-community-based-warning-saved-lives/), [Onlinekhabar: 2025 report ignored](https://english.onlinekhabar.com/rasuwa-flood-report-nepal.html), [Onlinekhabar: lessons](https://english.onlinekhabar.com/how-many-floods-to-react.html)

**Before the flood**
- Satellite imagery shows the glacier north of Langtang Lirung moving about 10 mm/month from Jan 8 to Aug 18, 2026, and **speeding up in the weeks before it collapsed**. Nobody was watching for it operationally.
- The corridor had flooded 13 months earlier (§1.5). A district report written after that flood recommended moving settlements from Timure to Betrawati, setting up a cross-border warning system, and assessing glacial lakes. **It was filed and not acted on.**
- No rain fell that morning. The warning thresholds were set for monsoon floods, and the Chinese/Nepali flash-flood warning system was built for glacial lake outbursts, not ice-rock avalanches.

**The flood (NPT)**
- 08:37: an ice-rock avalanche from the Lirung massif (seismic signal Ms 5.2). About 0.2 km² of ice and rock fell roughly 1.2 km and became a debris flow moving at about 180 km/h.
- 08:44: Gyirong Port destroyed. 08:50: the Syabrubesi gauge goes dead (last reading normal). 09:00–09:05: **DHM learns of the flood from a phone call** by the Rasuwa district office.
- 09:10: a head teacher in Trishuli gets **phone calls from people upstream** and evacuates about 900 students. The flood reaches the school at 09:20.
- 09:15–09:16 (DHM's figure; the PM told Parliament 09:35): SMS sent to 679,295 people. One resident received it at 09:54, after the flood. The text read, in full: *"A large flood has entered the Bhotekoshi River in Rasuwa from the Tibet side. Until further notice, residents along the banks of the Trishuli River (up to Muglin) are requested to remain in a safe location with high alert."* It was in Nepali only, gave no location detail or time to impact, and arrived three times.
- 09:20: Betrawati gauge goes dead. 11:26–11:43: the Malekhu gauge crosses the danger level and is then swept away. 14:14: Kalikhola peaks at 12.3 m. 16:00: Devghat peaks at 6.57 m. 18:30: Devghat falls back to about 4 m. **The flood took about 10 hours to travel the system and moved about 20 million m³ of extra water.**
- **Galchhi rose 9 m in 30 minutes.** Water reached settlements up to 80 m above the river. Timure sits about 8 m above the riverbed, and the flood rose more than 20 m.

**Response and evacuation**
- Officials were deployed nationally: about 21,465 security personnel and 14 helicopters on day 1, with 1,348 flights by Sep 9. Some villages (Tiru) could not be reached by helicopter until **day 15**. Tunnel rescues at hydropower projects continued until Sep 5.
- Nepal **declined foreign search and rescue teams** (citing coordination problems after the 2015 earthquake) and later accepted specialists. A "one-door" policy channeled all donations through the government. The International Charter (satellite imagery) was activated at 18:13 on day 1. HOT/OSM mapped damage.
- **Secondary risk:** a barrier lake of about 2 million m³ in Tibet overflowed on Aug 28, and rescue work stopped for about 3 hours. The lake drained by Aug 30. **This is the case where modeling the lake would actually have helped.**
- 37 holding centers housed up to 4,500 people. Families with damaged homes get Rs 15,000/month. The area was declared a disaster zone for 3 months.

**After the flood**
- About 1,454–1,497 dead and about 5,285–6,000 missing. 1.6 million people affected. 7,570 houses destroyed. **68 suspension bridges and 41 motorable bridges damaged** (33 suspension bridges beyond repair), and 69 km of road. 12 hydropower plants damaged, taking 430 MW (about 10–12% of national capacity) offline. 120 Nepal Telecom and 78 Ncell towers affected, with about 97% restored by Sep 4. Losses exceed $5B, about 15% of GDP.
- Bailey bridges and temporary footbridges are going in. Kathmandu 10 Action Points published (Sep 25, §4). A bill to allow relocation from high-risk areas is in draft. The law was changed so missing people can be declared dead after 45 days instead of 12 years.
- **Duration:** the flood lasted about 10 hours. Search and rescue ran for weeks. Recovery will take years.

### 1.4 Eastern Nepal rains and landslides (Ilam), Oct 3–6, 2025
Sources: [GDACS](https://www.gdacs.org/report.aspx?eventtype=FL&eventid=1103540), [Himalayan Times](https://thehimalayantimes.com/nepal/floods-landslides-kill-60-across-nepal-since-friday-night), [Onlinekhabar Ilam](https://english.onlinekhabar.com/17-killed-in-landslides-in-ilam.html), [Ilam aftermath](https://english.onlinekhabar.com/landslides-leave-ilam-reeling.html)

- **Before:** a late-monsoon low-pressure system brought more than 300 mm of rain in places (Ilam, Rautahat, Bara, Parsa). It was **forecast**. **[unverified]** The interim government (formed after the Sep 2025 Gen Z protests) declared public holidays and restricted vehicle travel ahead of the rain.
- **Event:** Oct 3–5. Houses were buried by landslides at night, often killing whole families (6 in one Tamang family in Ilam-6). Most deaths were in Ilam.
- **Response:** Armed Police teams went out village by village. Night driving was banned on the BP and Kantilokpath highways.
- **After:** 47–60+ dead (OCHA: 51; APF: 60), 39 of them in Ilam. 365 houses destroyed and 940 damaged. Rs 11.81B in damage in Ilam alone. **More than 200 landslide sites on the Mechi Highway.** Multi-year repairs. **Months later, money for permanent housing had not been released** because three levels of government had not coordinated.
- **This was a different kind of hazard:** rain-triggered, forecast in advance, and widespread. Deaths came from houses buried on slopes, not from flooding along rivers. Routing tools help less here. Warnings for specific slopes and specific houses help more.

### 1.5 Rasuwagadhi GLOF, Bhotekoshi/Lhende, Jul 8, 2025
Sources: [Wikipedia (2025 Nepal floods)](https://en.wikipedia.org/wiki/2025_Nepal_floods), [Onlinekhabar](https://english.onlinekhabar.com/rasuwa-flood-report-nepal.html)

- **Before:** a supraglacial lake in Tibet drained during the monsoon. **Nepal received no warning from China.**
- **Event:** about 03:00. The Miteri (Friendship) Bridge was destroyed, along with the customs yard, hundreds of trucks and electric vehicles, the Rasuwagadhi hydropower project, and the road from Syabrubesi to Rasuwagadhi.
- **Response:** about 55 people rescued. 9+ dead, 18 missing.
- **After:** a district review recommended a cross-border warning system, a glacial lake inventory, relocation of settlements from Timure to Betrawati, and risk studies before rebuilding. **None of it was done. The same corridor was hit 13 months later, about 100 times worse.**

### Context: Sep 2024 Kathmandu Valley floods (the baseline for response)
[Wikipedia](https://en.wikipedia.org/wiki/2024_Nepal_floods). Rain on Sep 26–29 (240–322 mm in 24 hours in Kathmandu, the most since 1970). About 224–250 dead. 37 highways blocked at 28 points, and only 9 of 37 open by Oct 1. 35 bodies recovered from vehicles buried on the Prithvi Highway. Measures: bans on night travel, schools closed for 3 days, flights cancelled, 30,000 security personnel. Also: the Aug 2024 Thame glacial lake outburst (135 people displaced) and the May 2025 Tilgau (Humla) glacial lake outburst.

---

## 2. How the response has changed, 2024 → Oct 2026

| Aspect | 2024–2025 | Aug 2026 | Oct 2026 |
|---|---|---|---|
| Detection | Gauge thresholds plus forecasts | Gauges destroyed within minutes. DHM learned **by phone** | Locals heard and saw the blockage. Officials learned 2–3 hours later |
| Warning | 1155 SMS by area (since 2016). Highway bans | SMS to 680k people: generic, Nepali-only, duplicated, late in places | SMS 20 minutes after official notice, which was *after* the first wave. **Community relay arrived about 3 hours earlier and saved lives** |
| Evacuation | No legal trigger. Up to individuals | No agency ordered an evacuation in real time. Residents and a head teacher decided themselves | Self-evacuation uphill on both banks. Police loudspeakers. Survivors credit "having seen Rasuwa a month earlier" |
| Coordination tools | BIPAD portal | **Setu Rapid launched Aug 26–27** (highway incidents, rescue and relief requests) | Drone teams, technical teams, Bailey bridge teams sent on day 1 |
| Policy | Reports not acted on (Melamchi 2021, Rasuwa 2025) | Kathmandu 10 Action Points. Cell broadcast task force (Sep 9). Relocation bill. NTC–DHM SMS agreement renewed (Jul 2026) | Same institutions, faster to mobilize, still reacting after the fact |

**The pattern:** each response is faster to *mobilize*, but **detection and warning still depend on people upstream making phone calls**, and official warnings still carry no actionable instruction ("where do I go, how long do I have, is the bridge safe?").

---

## 3. Apps and communication channels already in use

| Tool | Owner | Who uses it | What it does | Gap for our use case |
|---|---|---|---|---|
| **1155 SMS alerts** | DHM + Nepal Telecom/Ncell (since 2016, renewed Jul 2026) | Everyone on a carrier in the targeted area | Mass SMS to areas DHM draws on a map. Free | Generic text, Nepali only, slow, depends on the subscriber database, sent repeatedly |
| **Cell broadcast** | NDRRMA + Nepal Telecommunications Authority | Every phone in range, even with no SIM | **Not live.** Task force formed Sep 9, 2026, about Rs 100M budget. GSMA/ITU study says it reaches a zone in about 10 seconds and supports multiple languages | When it launches, it will need *content*: location, severity, what to do |
| **Nepal Weather Official app** | DHM + NITC (launched Jul 2026) | Public, Android and iOS, no login | Forecasts, push alerts (rain, lightning, flood, landslide), **trekking-area forecasts**, Nepali/English, **offline cache** | Weather and hazard alerts only. No routes or road status. Early bugs |
| **BIPAD portal and app** | NDRRMA | Public, officials | National incident database (verified, geo-points), real-time river and rain, alerts, exposure. **Public REST API** (`bipadportal.gov.np/api/v1/{incident,river,rain,alert}`) | A dashboard, not a guide to what to do. Reports are made by officials |
| **Setu Rapid** | NDRRMA + Department of Roads (built by Astra Labs and Naxa), launched Aug 2026 | Field app: **authorized staff only**. Web: public "Need Rescue / Need Relief / Donate" | Live map of highway incidents, responder locations, dispatch | **Highways only, staff only.** No trails, suspension bridges, or public road-status view. No prediction |
| **Hotlines** | Govt | Public | NEOC toll-free 1234, police 100. **[unverified]** Hello Sarkar 1111 | Voice only |
| **Community warning networks** | Communities and NGOs (East Rapti watch platform since 2002) | Villages | Trusted people relay what they see by phone or on foot | **This is what worked on Aug 26 and Oct 11.** Informal, unrecorded, does not scale |
| **Social and messaging apps** | Facebook, Viber, TikTok, WhatsApp | Most people | Footage, rumors, missing-person posts | Misinformation: 72 users ordered to remove AI-generated or graphic flood content. In **Sep 2025 the government blocked 26 platforms for several days** (which set off the Gen Z protests). Relying on one platform is risky |
| **Community missing-person sites** | Volunteers | Families | e.g. nepalflood2026.vercel.app combines SETU, NDRRMA, and police lists | Only useful after the event |
| **Trekker channels** | Manaslu Conservation Area checkpoints, trekking agencies' association, third-party apps (Trekguard) | Trekkers and guides | **Checkpoint counts of people entering** (98 on Oct 10). Third-party trail advisories | Nepali SMS does not reach foreigners in a language they read. No official warnings in English |
| **Satellite internet** | Starlink | n/a | Offered free service on Aug 30 "once permitted." **Not licensed in Nepal [status unverified]** | No backup communications when towers go down |
| **Sirens, loudspeakers, radio** | Local govt, police | Riverbank communities | Police used loudspeakers along the river on Oct 11. One former NDRRMA head dismissed manual sirens as "backward" | Works without the network |

**Pre-installed apps:** no evidence of any government disaster app that comes pre-installed. Nepal has no live cell broadcast or wireless emergency alert system. **[unverified]** Android's built-in emergency alerts would only work once the carriers turn on cell broadcast.

---

## 4. Forecasts and models for future disasters

- **Kathmandu 10 Action Points** (ICIMOD, NDRRMA, Switzerland; Sep 2026) [link](https://www.icimod.org/press-release/rasuwa-gyirong-floods-prompt-global-call-for-stronger-action-on-cascading-mountain-risks/). Relevant points:
  1. Redesign warning triggers for **sudden-onset** hazards.
  2. Build an inventory of multi-hazard hotspots from satellite monitoring, with **impact-based forecasting**.
  3. Share **decision-ready information** across borders instead of raw data.
  4. Build a shared data portal to break down agency silos.
  Swiss example: in Blatten (2025), an ice-rock avalanche was detected early and the whole village was evacuated before it hit.
- **Glacial lakes** (ICIMOD/UNDP 2020): 3,624 lakes assessed, **47 potentially dangerous** (21 in Nepal, 25 in China, 1 in India). By basin: 42 Koshi, 3 Gandaki, 2 Karnali. Estimated people exposed: Lumuchimi (Bhote Koshi) 16,313, Imja 7,762, Tsho Rolpa 5,183. Nepal has had at least 24 glacial lake outburst floods. [link](https://english.onlinekhabar.com/flood-glacier-risk-nepal.html)
- **But both 2026 disasters were ice-rock avalanches, not lake outbursts.** Monitoring lakes alone misses them. About 83% of Nepal's mountain and hill area is exposed to landslides or lake outbursts.
- **Remaining risk in Langtang:** China's water ministry says the glaciers around the impact crater **are still at risk of collapsing** (Sep 1). [link](https://english.onlinekhabar.com/drone-images-chinese-glacier.html)
- **Upper Chumnubri (Budhi Gandaki):** two blockage floods in 5 weeks (Sep 6, Oct 11) and repeated blocking and releasing on Oct 11. Treat the slopes as **actively unstable**.
- **Repeat-corridor pattern:** Bhotekoshi in Jul 2025, then Aug 2026. Namrung on Sep 6, then Oct 11. **The best predictor of the next event is the last one.**
- **Chronic road hotspots:** Krishna Bhir (Prithvi Highway), more than 200 sites on the Mechi Highway, the Mugling–Narayanghat road. All face the 2027 monsoon.
- **Climate:** glaciers are melting about 65% faster and permafrost is degrading. **[unverified]** A 2026–27 El Niño is listed on Wikipedia, but its effect on the 2027 monsoon in Nepal is not established.
- **Seasonal calendar:** now through November is trekking season and the Dashain/Tihar travel period, with more people on trails and roads. The monsoon runs June–September. Avalanche-triggered floods happen *outside* the rain season (Aug 26 and Oct 11 both had no rain).

---

## 5. Gap analysis for our project

| Gap (evidence) | Does it already exist? | Fits our project? |
|---|---|---|
| **Upstream observation → downstream alert pipeline** ("river stopped / roar / blocked"). On Oct 11 it gave about 3 hours of lead time, all by phone | No. Informal phone chains only | **Strong fit.** Structured intake of reports, then estimated time to impact for every settlement downstream |
| **Detecting a blockage from a falling river level** (flow nearly stopped at Sirdibas at 08:20, and locals noticed the river stop) | No. DHM triggers only on *rising* levels | **Strong fit, simple to build, uses data we have** (BIPAD/DHM river feeds). Rule: a sharp drop with no rain means a likely upstream blockage |
| **Warnings that say what to do** (where to go, how high, how long, which bridge to avoid), multilingual | No. Generic Nepali SMS | **Strong fit.** This is the generative piece. Could feed cell broadcast later |
| **Live status of trails and suspension bridges** (6 lost on Oct 11, 68 in Aug) | Setu Rapid covers **highways only, staff only** | Fits, but the data is thin |
| **Information for trekkers and foreigners** (100+ stranded, Nepali-only SMS) | Third-party advisories only | Fits (English alerts, checkpoint counts) |
| **Secondary barrier-lake risk over days** (Tibet lake, Aug 28) | Assessed manually by China and Nepal | Moderate fit: our lake model belongs in this post-event phase |
| **Splitting crowds across routes** | n/a | **Weak evidence.** No reports of congested routes. Consider dropping or shrinking it to "choose a bank and a high-ground target, avoid failing bridges" |
| Rescue and relief requests, donations | Setu Rapid web | **Do not build** |
| Hazard dashboard and incident database | BIPAD | **Do not build.** Use it as a data source |
| Weather forecasts and push alerts | Nepal Weather app | **Do not build** |

## 6. Corrections to the current plan

- "There is no live gauge on the Budhi Gandaki in DHM's public network." **False.** The Arughat gauge exists (warning 4.5 m, danger 5 m). It peaked at 8.43 m, then was destroyed.
- "A landslide blocked the river and then burst." Partly true. The preliminary cause is an avalanche that blocked the river, which then burst **repeatedly within hours**. It was not a lake that filled slowly.
- "More than 1,400 dead." Current figures are about 1,454–1,497 dead and 5,285–6,000 missing.
- "Devghat 6.57 m, below 7.3 m warning level." 6.57 m is confirmed. **The 7.3 m warning level is not verified.**
- "Three days after the route was declared safe." **Not verified.** What is verified: the route was closed Sep 6 after the Namrung flood, and about 98 trekkers entered on Oct 10.
- "Historical gauge data locked." The DHM endpoint is locked, but the **BIPAD API exposes river and rain history**. Check how far back it goes.

---

## 7. State of the art: what exists, how good it is, and whether we reuse it

Verified links are inline. Claims marked **[from memory]** come from the literature and have not been rechecked today.

### 7.1 Forecasting *where* a flood will go *before* it happens

| Approach | Examples | How good | Fits our hazard? | Our decision |
|---|---|---|---|---|
| **AI riverine forecasting** | [Google Flood Hub / Flood Forecasting API](https://developers.google.com/flood-forecasting) (150+ countries, up to 7-day lead time, inundation maps, CC BY 4.0, API needs a waitlist) | Strong for large **rain-driven** floods. **[from memory]** Nearing et al., *Nature* 2024: a 5-day lead in ungauged basins is about as reliable as GloFAS same-day nowcasts | **No.** Aug 26 and Oct 11 had no rain. A rainfall-runoff model cannot see an avalanche or a landslide dam | Don't build. Mention it as the monsoon layer we would consume |
| **Physics/global riverine** | [GloFAS / CEMS](https://www.globalfloods.eu/), DHM's own deterministic and ensemble forecasts, ICIMOD regional flood outlook | Good for large monsoon rivers, coarse for steep gorges | No, same reason | Don't build |
| **Debris-flow and outburst scenario simulation** | **[from memory]** r.avaflow (open source, GRASS + R; used for Chamoli 2021), RAMMS (commercial), HEC-RAS 2D (free, closed source), LISFLOOD-FP (open source) | Accurate once calibrated, but needs **the source volume and location**, which you only know after the event, plus hours of compute and expert tuning | Used *before* the season to map hazard for specific lakes (Tsho Rolpa, Imja). **Too slow and too dependent on unknown inputs to run live** | Don't build or port it (it probably won't install on s390x). Use a fast terrain approximation instead (§7.4) |
| **Hazard and susceptibility maps** | ICIMOD/UNDP glacial lake inventory (47 dangerous lakes), landslide susceptibility maps, Kathmandu 10 Action Points hotspot inventory (planned) | They show where risk exists, not when it will hit | Useful as background layers | Use if quick to obtain, otherwise skip |

**Bottom line:** nobody can forecast *when* an ice-rock avalanche or landslide-dam outburst will happen. The state of the art is **(a)** mapping hazard before the season, plus **(b)** detecting the event fast and warning everyone downstream within minutes.

### 7.2 Detecting the event (where lead time comes from)

| Method | Status | Lead time it gives |
|---|---|---|
| **Upstream human observation** (rumbling, river stops, landslide seen) | What actually worked on Aug 26 and Oct 11, but informally, by phone | Oct 11: about **2.5–3 h** before Arughat. Aug 26: about 10 min at Trishuli school |
| **Gauge thresholds (rising)** | DHM operational | Minutes, and gauges die at the peak |
| **Gauge *drop* (river stops = blockage upstream)** | **Not used operationally in Nepal** as far as we found. Locals noticed it, and Sirdibas flow "almost stopped" at 08:20 | Potentially hours on dammed rivers |
| **Seismic detection of mass movements** | USGS and GFZ picked up Aug 26 at 08:37 (Ms 5.2) and Oct 11 (about M3.5 equivalent). Identifying it as an avalanche took hours. **[from memory]** Research systems exist (e.g. Illgraben debris-flow alarms in Switzerland) | Minutes, if automated. Not operational in Nepal |
| **Satellite monitoring of slopes and glaciers before collapse** | Langtang glacier acceleration was visible in imagery from Jan–Aug 2026 but not watched. In Blatten, Switzerland (2025), monitoring led to evacuation before the collapse | Days to weeks, for a few slopes being watched |
| **Fixed GLOF warning systems** (sirens at Tsho Rolpa, Imja) | Operational for specific lakes | Minutes to hours, but only for those lakes |

### 7.3 Evacuation modeling

| Approach | Examples | Fit |
|---|---|---|
| **Walking time to safety on terrain** (anisotropic least-cost path, slope + land cover) | [USGS Pedestrian Evacuation Analyst (PEAT)](https://www.usgs.gov/software/pedestrian-evacuation-analyst-tool): built for tsunamis, flash floods and lahars. Maps "time to high ground" for every location and counts people per time band | **Best fit.** Matches how people actually evacuated (on foot, uphill). PEAT itself is an ArcGIS extension for Windows and **can't run on L1CC**, but the method is easy to reimplement (Dijkstra on a DEM grid with Tobler cost) |
| **Agent-based crowd and traffic simulation** | **[from memory]** MATSim, SUMO, JuPedSim | Built for cities and road networks. Overkill here, since no congestion has been documented |
| **"Can they make it?" comparison** (flood arrival time vs. warning delay + walk time) | Standard in tsunami evacuation planning **[from memory]** (Wood & Schmidtlein) | **This is what we should optimize: the number of people whose slack is ≥ 0** |

### 7.4 Practical fast approximation we can build in 24 hours (all open methods)

1. **Flood path:** follow the river network downstream from the trigger point (OSM waterways, or D8 flow on the DEM).
2. **Arrival time:** distance along the river ÷ wave speed. From our two replays, after the first ~20 km the wave travelled at roughly **20–40 km/h** (Oct 11: about 60 km to Arughat in about 2–2.5 h. Aug 26: Gyirong 08:44 → Malekhu 11:26 → Devghat 15:20). Exact river distances are not yet measured, so calibrate them.
3. **Flood height:** **HAND** (Height Above Nearest Drainage), meaning DEM elevation minus the elevation of the nearest river cell, compared against a flood-height envelope that shrinks downstream. Calibration points: 20–25 m at Salleri, 8.43 m at Arughat, more than 20 m at Timure, up to 80 m above the river in places on Aug 26, 6.57 m at Devghat.
4. **Safety:** cells with HAND > predicted height + margin.
5. **Walking time:** Dijkstra over the DEM grid with Tobler cost, **without crossing the river except at bridges**.
6. **Slack** = arrival time − (warning delay + walking time). Lives at risk = population with slack < 0.

### 7.5 Is congestion a real problem here?

- **On foot, same bank, uphill:** no evidence of congestion. People spread out across the hillside.
- **Bottlenecks that could matter:** (a) **suspension bridges** (narrow, single file) where high ground is only on the other bank; (b) narrow trail sections in the gorge; (c) **places where people gather and can't get out quickly**: 300+ vehicles queued at Rasuwagadhi customs, 900 hydropower workers in tunnels, herders in riverbed sheds, trekkers on the valley-floor trail.
- **Approach:** don't build a general congestion optimizer. **Check capacity only at bridges and other single-file points** (people needing to cross × time per person versus the slack). Separately, flag places where people gather on the valley floor for priority warnings.

---

## 8. More events for calibration and validation (beyond the two from 2026)

For the time-to-safety engine, an event is useful if it has: **(a) arrival times at known points along the river**, **(b) observed flood heights or a flood footprint**, **(c) a damage map**. How warnings were communicated doesn't matter for calibration, so events in India, Pakistan and Switzerland count.
Status: **[from memory]** unless a link is given. Before entering numbers, check them against the paper or report named.

### Sudden-onset floods in the same category (best calibration value)
| Event | Type | Why useful | Primary sources to pull numbers from |
|---|---|---|---|
| **Chamoli, Uttarakhand, India, Feb 7 2021** | Rock-ice avalanche → debris flow (Rishiganga/Dhauliganga/Alaknanda) | Very well documented: front speeds, arrival times at hydropower sites and towns, gauge records, about 200 dead/missing. The closest analog to Aug 26 | Shugar et al. 2021, *Science*. India's Central Water Commission gauges. Wikipedia: [2021 Uttarakhand flood](https://en.wikipedia.org/wiki/2021_Uttarakhand_flood) |
| **South Lhonak GLOF, Sikkim, India, Oct 3–4 2023** | Glacial-lake outburst plus landslide into the lake → Teesta | Long travel path (hundreds of km) with several gauges and timestamped dam failure (Teesta III at Chungthang about midnight). About 92 dead. Good for how the flood weakens downstream | Sattar et al. 2025, *Science* (multi-hazard cascade). Wikipedia: [2023 Sikkim flash floods](https://en.wikipedia.org/wiki/2023_Sikkim_flash_floods) |
| **Melamchi, Nepal, Jun 15 2021** | Debris flow/flood (Melamchi Bazaar destroyed) | Nepal, with DHM gauges. Wikipedia notes locals sensed the river damming and were moved uphill | ICIMOD rapid assessments (2021). [Wikipedia](https://en.wikipedia.org/wiki/2021_Melamchi_flood) |
| **Seti River, Pokhara, Nepal, May 5 2012** | Ice/rock avalanche → flash flood, 9.1 m deep | Nepal, a short and well-studied reach (Kharapani). Wikipedia: [May 2012 Nepal floods](https://en.wikipedia.org/wiki/May_2012_Nepal_floods) | Kargel et al. 2013 and others |
| Bhotekoshi GLOF, Jul 5 2016; Thame GLOF, Aug 16 2024; Rasuwagadhi, Jul 8 2025 | GLOFs | Same corridors as our events. Smaller | DHM/ICIMOD reports |
| Kedarnath, Uttarakhand, Jun 2013 | Rain plus lake breach | Huge death toll, but **mixed with rain**, so a weaker analog | Many papers |

### Landslide-dam events (for the P3 lake / time-to-breach model)
| Event | Facts (Wikipedia, [Landslide damming in Nepal](https://en.wikipedia.org/wiki/Landslide_damming_(Nepal))) |
|---|---|
| **Jure/Sunkoshi, Nepal, Aug 2 2014** | 5.5 M m³ landslide, lake behind it, Araniko Highway cut. A days-long blockage with downstream evacuation. [Wikipedia](https://en.wikipedia.org/wiki/2014_Sunkoshi_blockage) |
| Kali Gandaki (Baseri), May 2015 | River dammed **for 16 hours**. 27 houses buried. Downstream evacuation |
| Myagdi (Darbang), Sep 1988 | Rockslide dam. 109 killed by the slide, plus 71 by the outburst |
| Marsyangdi (Gogane) 2015, Tamor 2016, Badigad 2018 (6 h), Arun 2020 | Smaller blockages, a few hours to days |
| **Attabad, Pakistan, 2010** | A lake that lasted months (21 km, >100 m deep). Overtopped slowly. Shows the days-to-months case |
| Blatten, Switzerland, May 2025 | Monitoring → **village evacuated about 9 days before** the glacier collapse, which buried the village and blocked the Lonza. The positive example (ICIMOD cites it) |

### Earthquakes
- **We don't model earthquake shaking.** There's no lead time to work with (earthquake early warning gives seconds), and it isn't an evacuation-routing problem.
- **We do cover earthquake *secondary* hazards:** quake-triggered landslides blocking rivers and the outbursts that follow, e.g. the 2015 Gorkha earthquake blocking the Tom River in Manaslu, and the Langtang avalanche. In our pipeline that's just another trigger source.
- Tsunamis are where the time-to-safety method (USGS PEAT) came from, which supports the method but isn't in our scope.

### Where to get flood footprints and damage maps for other events
- **[from memory]** Copernicus Emergency Management Service rapid-mapping activations, the International Charter (activated Aug 26 2026), and UNOSAT products: free vector flood and damage extents for many of the events above. Check each event's activation.
- OSM/HOT damage tagging (Aug 2026 Nepal).

### How the extra events get used
Build a small table with one row per observation point: `(event, distance from source along river km, travel time min, peak height m, channel slope, valley width, source volume if known)`. Fit **wave speed and height decay vs. distance** across events, and validate **leave-one-event-out**. This turns the "calibration" into a real cross-event predictive model, which is better evidence than tuning to Oct 11 alone.
