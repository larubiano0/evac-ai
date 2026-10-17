"""Template alerts (no LLM). Facts come only from computed values.

Two lengths per language:
  short : trigger message. English <=160 chars (1 GSM-7 SMS); Nepali <=70 chars (1 UCS-2 SMS),
          also fits a Meshtastic LoRa payload (~200 bytes) and a cell-broadcast page.
  full  : the per-settlement plan (offline page / printout).
NEPALI TEXT IS A DRAFT: it must be reviewed by the team's Nepali reader before any demo claim.
"""
NE_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")
NE_REVIEWED = True    # reviewed and approved by Aayush Poudel (native Nepali reader), Sat Oct 17


def _ne(s):
    return str(s).translate(NE_DIGITS)


def short_en(place, arrival):
    return f"FLOOD ALERT {place}: wave from ~{arrival}. Go UPHILL now on your side of the river. Do not cross bridges."


def short_ne(place, arrival):
    # <=70 chars target (one UCS-2 SMS); uses the Devanagari place name when OSM has one
    return f"बाढी! {place} {_ne(arrival)} देखि। तुरुन्त माथि जानुहोस्, पुल नतर्नुहोस्।"


def full_en(s, bridges, now_hhmm=None):
    mins = s.get("minutes_left")
    when = f"from about {s['arrival_early']}" + (f" ({mins:.0f} min from the warning)" if mins is not None else "")
    br = "; ".join(bridges) if bridges else "any bridge over the river"
    return (f"FLOOD ALERT for {s['name']}. A flood wave may reach the river bank here {when}. "
            f"Go uphill NOW. Safe ground is about {max(1, round(s['walk_min_max']))} minutes' walk uphill on your side of the river. "
            f"Do not cross the river and do not stand on bridges: {br}. "
            f"Take children, elderly and disabled people first. Do not go back for animals or belongings. "
            f"Stay on high ground until the authorities say it is safe; more waves can follow.")


def full_ne(s, bridges):
    br = "; ".join(bridges) if bridges else "नदीमाथिका कुनै पनि पुल"
    return (f"{s['name']} का लागि बाढी चेतावनी। करिब {_ne(s['arrival_early'])} देखि यहाँको नदी किनारमा बाढी आउन सक्छ। "
            f"अहिल्यै माथि जानुहोस्। सुरक्षित ठाउँ नदीको यही किनारतर्फ करिब {_ne(max(1, round(s['walk_min_max'])))} मिनेट उकालो हिँडेपछि छ। "
            f"नदी नतर्नुहोस् र पुलमा नबस्नुहोस्: {br}। "
            f"बालबालिका, वृद्धवृद्धा र अपाङ्गता भएका व्यक्तिलाई पहिले लैजानुहोस्। पशु वा सामान लिन फर्केर नजानुहोस्। "
            f"अधिकारीहरूले सुरक्षित भनेपछि मात्र फर्कनुहोस्; अर्को बाढी पनि आउन सक्छ।")


def build(settlement, bridges_near, warn_hhmm, warn_min_after_burst):
    s = dict(settlement)
    s["minutes_left"] = s["arrival_minutes_after_burst"] - warn_min_after_burst
    names_en = list(dict.fromkeys(b["label"] for b in bridges_near))[:3]
    names_ne = list(dict.fromkeys(b["label_ne"] for b in bridges_near))[:3]
    s_ne = dict(s, name=s.get("name_ne") or s["name"])
    a = {"short_en": short_en(s["name"], s["arrival_early"]), "short_ne": short_ne(s_ne["name"], s["arrival_early"]),
         "full_en": full_en(s, names_en), "full_ne": full_ne(s_ne, names_ne), "nepali_reviewed": NE_REVIEWED}
    a["short_en_chars"], a["short_ne_chars"] = len(a["short_en"]), len(a["short_ne"])
    a["short_ne_bytes"] = len(a["short_ne"].encode("utf-8"))
    return a
