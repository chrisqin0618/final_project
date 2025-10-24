"""
Life Restart Simulator - CLI (ASCII-only, English-only)
Usage:
    python3 life_restart.py
"""

import random
import sys
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional, Set

# ------------- Auth (Register/Login) -------------

def auth_flow() -> Tuple[str, str]:
    """Force user to register first, then return to login page to login."""
    print("=== Life Restart Simulator (Login Required) ===")
    user_db = {}
    # Register
    print("\n-- Register --")
    while True:
        u = input("Choose a username: ").strip()
        p = input("Choose a password: ").strip()
        if not u or not p:
            print("Username/password cannot be empty.")
            continue
        if u in user_db:
            print("Username already exists.")
            continue
        user_db[u] = p
        print("Registration successful.")
        break
    # Back to login
    print("\n-- Login --")
    for _ in range(5):
        u2 = input("Username: ").strip()
        p2 = input("Password: ").strip()
        if u2 in user_db and user_db[u2] == p2:
            print("Login successful.\n")
            return (u2, p2)
        print("Invalid credentials, try again.")
    print("Too many failed attempts. Exiting.")
    raise SystemExit(1)

# ------------- Data Models -------------

@dataclass
class Stats:
    health: int     # 0..100
    wealth: int     # 0..100
    knowledge: int  # 0..100
    karma: int      # 0..100
    charisma: int   # 0..100

    def clamp(self) -> "Stats":
        def c(v, lo, hi):
            return max(lo, min(hi, v))
        return Stats(
            health=c(self.health, 0, 100),
            wealth=c(self.wealth, 0, 100),
            knowledge=c(self.knowledge, 0, 100),
            karma=c(self.karma, 0, 100),
            charisma=c(self.charisma, 0, 100),
        )

    def apply(self, delta: Dict[str, int]) -> "Stats":
        d = asdict(self)
        for k, v in (delta or {}).items():
            if k in d:
                d[k] += v
        return Stats(**d).clamp()

    def pretty(self) -> str:
        return "H{h} W{w} K{k} Ka{ka} Ch{ch}".format(
            h=self.health, w=self.wealth, k=self.knowledge, ka=self.karma, ch=self.charisma
        )

@dataclass
class Option:
    text: str
    delta: Dict[str, int]
    tags_set: Set[str]
    requires: Set[str]
    risk_death: float
    swing_prob: float
    origin: str            # "base"/"dyn"/"milestone"
    template_id: str

# ------------- Content -------------

ERAS: List[Tuple[str, str]] = [
    ("modern", "Modern (2000s)"),
    ("tang", "Ancient China - Tang Dynasty"),
    ("habsburg", "Habsburg Europe (1700s)"),
    ("prehistoric", "Mythic Prehistory"),
]

NATIONALITIES: List[Tuple[str, str]] = [
    ("cn", "China"),
    ("au", "Australia"),
    ("at", "Austria"),
    ("us", "United States"),
    ("custom", "Wanderer (no fixed nation)"),
]

BIRTHS: List[Tuple[str, str]] = [
    ("rich", "Born Noble/Rich"),
    ("middle", "Born Middle Class"),
    ("poor", "Born Poor"),
]

AGE_BANDS: List[Tuple[str, Tuple[int, int]]] = [
    ("infant", (0, 2)),
    ("child", (3, 12)),
    ("teen", (13, 17)),
    ("young_adult", (18, 29)),
    ("adult", (30, 59)),
    ("elder", (60, 120)),
]

CHAPTER_LIMIT = 16
MAX_AGE = 100
AGE_STEP_MIN_MAX = (1, 6)
ENV_TRIGGER_PROB = 0.35
MILESTONES = [7, 18, 24, 30, 50]

# Achievement threshold for positive endings
ACHIEVEMENT_TARGET = 30

BIRTH_MODS: Dict[str, Dict[str, int]] = {
    "rich":   {"wealth": 10, "health": 2, "charisma": 2},
    "middle": {"wealth": 4},
    "poor":   {"wealth": 1, "knowledge": 1, "karma": 1},
}

# (Era events / triggers data)
ERA_AGE_EVENTS: Dict[str, Dict[str, List[Tuple[str, Dict[str, int]]]]] = {
    "modern": {
        "infant": [
            ("You babble at a mobile of planets.", {"knowledge": 1}),
            ("You catch a cold but recover quickly.", {"health": -1, "karma": 1}),
            ("A caregiver reads picture books to you.", {"knowledge": 1, "charisma": 1}),
        ],
        "child": [
            ("You discover the library's kids corner.", {"knowledge": 3}),
            ("You join a weekend sport team.", {"health": 2, "charisma": 1}),
            ("You share snacks at recess.", {"wealth": -1, "karma": 1, "charisma": 1}),
        ],
        "teen": [
            ("You win a science fair with a scrappy project.", {"knowledge": 4, "charisma": 1}),
            ("You doomscroll late into the night.", {"knowledge": -2, "health": -2}),
            ("You volunteer for a local shelter.", {"karma": 2, "charisma": 1}),
        ],
        "young_adult": [
            ("A scholarship offer appears in your inbox.", {"knowledge": 6, "karma": 1}),
            ("You build an open-source tool that gains stars.", {"knowledge": 5, "wealth": 3}),
            ("Start-up burns cash; you learn resilience.", {"wealth": -4, "knowledge": 2}),
        ],
        "adult": [
            ("You lead a small team through a tough release.", {"charisma": 2, "knowledge": 2}),
            ("You invest steadily and rebalance your portfolio.", {"wealth": 3}),
            ("You neglect exercise during crunch time.", {"health": -2}),
        ],
        "elder": [
            ("You mentor juniors and publish tutorials.", {"knowledge": 2, "karma": 2}),
            ("You take up brisk walks by the coast.", {"health": 2}),
            ("You donate to an open access initiative.", {"wealth": -2, "karma": 2}),
        ],
    },
    "tang": {
        "infant": [
            ("A gentle lullaby soothes your sleep.", {"health": 1}),
            ("A village healer blesses you with herbs.", {"karma": 1, "health": 1}),
            ("Neighbors gift you a silk charm.", {"charisma": 1}),
        ],
        "child": [
            ("A poet teaches you regulated verse basics.", {"knowledge": 3, "charisma": 1}),
            ("You practice calligraphy on scrap bamboo.", {"knowledge": 2}),
            ("You learn zithers' simple scales.", {"charisma": 1}),
        ],
        "teen": [
            ("Rumors of imperial exams reach your county.", {"knowledge": 3}),
            ("You learn courtesy rites from a traveling scholar.", {"charisma": 2}),
            ("You copy classics by lamplight.", {"knowledge": 2, "health": -1}),
        ],
        "young_adult": [
            ("You journey to the capital for the exams.", {"knowledge": 4, "charisma": 1}),
            ("Court intrigue: choose allies carefully.", {"charisma": 1, "wealth": 2}),
            ("You study under a stern examiner.", {"knowledge": 3, "health": -1}),
        ],
        "adult": [
            ("You mentor village pupils for the shengyuan.", {"knowledge": 3, "karma": 1}),
            ("Bandits harry the road; you escape wounded.", {"health": -3, "karma": 1}),
            ("You manage granary ledgers in a famine year.", {"wealth": 1, "karma": -1}),
        ],
        "elder": [
            ("Your verses enter a local anthology.", {"charisma": 2, "knowledge": 2}),
            ("You advise younger scholars under the plum tree.", {"karma": 2}),
            ("You retire to quiet tea and bamboo shadows.", {"health": 1}),
        ],
    },
    "habsburg": {
        "infant": [
            ("A nursemaid hums a courtly tune.", {"health": 1}),
            ("A family crest is embroidered for you.", {"charisma": 1}),
            ("A physician checks your temperament.", {"health": 1}),
        ],
        "child": [
            ("A tutor drills you in etiquette and letters.", {"charisma": 2, "knowledge": 1}),
            ("You learn a simple minuet.", {"charisma": 1}),
            ("You tour the city market with a steward.", {"knowledge": 1, "wealth": 1}),
        ],
        "teen": [
            ("You observe a salon from the side of the room.", {"knowledge": 2, "charisma": 1}),
            ("You study trade ledgers with a steward.", {"knowledge": 2, "wealth": 1}),
            ("You practice languages with visiting cousins.", {"charisma": 1, "knowledge": 1}),
        ],
        "young_adult": [
            ("A diplomatic ball opens trade opportunities.", {"wealth": 4, "charisma": 1}),
            ("Patron a composer; salons praise your taste.", {"charisma": 3, "knowledge": 2}),
            ("You shadow an envoy in negotiations.", {"knowledge": 2, "charisma": 1}),
        ],
        "adult": [
            ("Inheritance dispute among cousins.", {"wealth": -3, "charisma": 1}),
            ("You negotiate a minor border tariff.", {"wealth": 3, "charisma": 1}),
            ("You sponsor an artisans' guild.", {"charisma": 1, "karma": 1}),
        ],
        "elder": [
            ("You sponsor a charity hospital in the city.", {"karma": 2, "wealth": -2}),
            ("Your household becomes a haven for artists.", {"charisma": 2}),
            ("You compile letters into a family chronicle.", {"knowledge": 2}),
        ],
    },
    "prehistoric": {
        "infant": [
            ("You nap by the hearth; embers crackle.", {"health": 1}),
            ("Elders draw a spiral on your brow.", {"karma": 1}),
            ("You grasp at beads made of bone.", {"charisma": 1}),
        ],
        "child": [
            ("You learn to weave grasses into cord.", {"knowledge": 2}),
            ("You chase lizards between sun-warmed rocks.", {"health": 1}),
            ("You collect bright stones for elders.", {"karma": 1}),
        ],
        "teen": [
            ("Hunt small game with an elder.", {"health": -1, "charisma": 1}),
            ("Cave paintings whisper patterns.", {"knowledge": 3}),
            ("You keep the fire through a storm.", {"karma": 1, "health": -1}),
        ],
        "young_adult": [
            ("You befriend a fire spirit.", {"health": 2, "karma": 2}),
            ("Hunt a thunder-beast with obsidian spear.", {"health": -3, "charisma": 2}),
            ("You map a new pass across the ridge.", {"knowledge": 2, "charisma": 1}),
        ],
        "adult": [
            ("You discover a rich flint seam by the river.", {"wealth": 3, "knowledge": 1}),
            ("A rival clan tests your borders.", {"charisma": 1, "health": -1}),
            ("You tame pack beasts for travel.", {"wealth": 1, "health": 1}),
        ],
        "elder": [
            ("A shaman marks you as twice-born.", {"karma": 3}),
            ("You teach star paths to the young.", {"knowledge": 2, "karma": 1}),
            ("You guide a migration to gentler lands.", {"charisma": 1, "knowledge": 1}),
        ],
    },
}

ENV_TRIGGERS: Dict[str, Dict[str, List[Tuple[str, Dict[str, int]]]]] = {
    "modern": {
        "child": [("Neighborhood fair boosts your mood.", {"karma": 1, "charisma": 1})],
        "teen": [("A viral challenge distracts your study.", {"knowledge": -1})],
        "young_adult": [("Coworker shares a gym routine.", {"health": 1})],
        "adult": [("Market dip tests your patience.", {"wealth": -1})],
        "elder": [("Community tech club invites you to speak.", {"charisma": 1, "knowledge": 1})],
    },
    "tang": {
        "child": [("Spring festival lanterns lift your spirit.", {"karma": 1})],
        "teen": [("Local magistrate posts a new edict.", {"knowledge": 1})],
        "young_adult": [("Monks offer tea and quiet counsel.", {"karma": 1, "health": 1})],
        "adult": [("A drought threatens harvests.", {"wealth": -1})],
        "elder": [("Chrysanthemum viewing clears your mind.", {"health": 1})],
    },
    "habsburg": {
        "child": [("A visiting painter sketches your profile.", {"charisma": 1})],
        "teen": [("Estate steward shares a coin trick.", {"wealth": 1})],
        "young_adult": [("A court rumor requires discretion.", {"charisma": 1})],
        "adult": [("Merchants bring news of new routes.", {"knowledge": 1})],
        "elder": [("A chapel choir stirs old memories.", {"karma": 1})],
    },
    "prehistoric": {
        "child": [("A sudden rain fills stone basins.", {"wealth": 1})],
        "teen": [("You learn a safer way to tan hides.", {"knowledge": 1})],
        "young_adult": [("Aurora ripples; the camp feels blessed.", {"karma": 1})],
        "adult": [("A new berry patch is found.", {"wealth": 1})],
        "elder": [("Warm springs ease your joints.", {"health": 1})],
    },
}

TIME_RIFTS = [
    ("A shimmering rift appears...", "other"),
    ("A clockwork phoenix offers a second chance.", "maybe"),
    ("The Moon turns, years rewind like silk.", "any"),
]

# ------------- Mechanics & Helpers -------------

def label_of(options: List[Tuple[str, str]], key: str) -> str:
    for k, label in options:
        if k == key:
            return label
    return key

def starting_stats(birth_key: str) -> Stats:
    base = Stats(health=10, wealth=5, knowledge=5, karma=5, charisma=5)
    mod = BIRTH_MODS.get(birth_key, {})
    return base.apply(mod)

def pick(seq):
    return random.choice(seq)

def current_band(age: int) -> str:
    for band, (lo, hi) in AGE_BANDS:
        if lo <= age <= hi:
            return band
    return "elder"

def open_time_rift(current_era: str) -> str:
    label, mode = pick(TIME_RIFTS)
    if mode == "other":
        other = [k for (k, _label) in ERAS if k != current_era]
        next_era = pick(other)
    elif mode == "maybe":
        next_era = current_era if random.random() < 0.5 else pick([k for (k, _label) in ERAS])
    else:
        next_era = pick([k for (k, _label) in ERAS])
    print("Time Rift: {0}".format(label))
    print("You tumble into {0}!".format(label_of(ERAS, next_era)))
    return next_era

def score(stats: Stats) -> float:
    return (
        stats.health * 1.1
        + stats.wealth * 1.2
        + stats.knowledge * 1.1
        + stats.karma * 0.8
        + stats.charisma * 0.9
    )

def ending_for(stats: Stats, era_key: str) -> str:
    s = score(stats)
    if stats.health <= 0:
        return "A life burned too fast. You fade before your tale completes."
    if s >= 240:
        if era_key == "modern":
            return "You mentor others, open-access your research, and retire to the coast, content."
        if era_key == "tang":
            return "Your poems enter the anthology; officials whisper your name with reverence."
        if era_key == "habsburg":
            return "You become a deft diplomat; peace and prosperity mark your house."
        if era_key == "prehistoric":
            return "Tribe sings your legend: the one who stole fire twice and led the great migration."
    if s >= 180:
        return "A steady life: friendships held, lessons learned, and a few bright victories."
    if s >= 120:
        return "You wander, but the map grows clearer. Not perfect, not wasted, simply human."
    return "A rough road. Yet even small kindness echoes beyond the page."

# ---------- Delta utilities & detailed reporting ----------

STATS_KEYS = ["health", "wealth", "knowledge", "karma", "charisma"]

def add_delta(a: Dict[str,int], b: Dict[str,int]) -> Dict[str,int]:
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) + v
    return out

def fmt_delta(d: Dict[str,int]) -> str:
    parts = []
    for k in STATS_KEYS:
        v = d.get(k, 0)
        if v != 0:
            sign = "+" if v > 0 else ""
            parts.append(f"{k}:{sign}{v}")
    return ", ".join(parts) if parts else "no change"

def make_preview_text(o: Option) -> str:
    tips = []
    if o.risk_death > 0:
        tips.append(f"risk≈{int(o.risk_death*100)}%")
    if o.swing_prob > 0 and sum(o.delta.values()) < 0:
        tips.append(f"swing≈{int(o.swing_prob*100)}%")
    preview = fmt_delta(o.delta)
    if tips:
        return f"{preview}  [{' '.join(tips)}]"
    return preview

# ------------- Dynamic templates -------------

ERA_FLAVOR = {
    "modern":   {"study": "Focus on study and projects.",
                 "work": "Take a full-time position.",
                 "retire": "File paperwork and plan a modest retirement.",
                 "risk": "Take a risky shortcut at work.",
                 "health": "Commit to disciplined training.",
                 "network": "Network at a meetup.",
                 "rest": "Take a mental health break."},
    "tang":     {"study": "Copy classics and drill essays.",
                 "work": "Enter an apprenticeship in the yamen.",
                 "retire": "Withdraw from office to a quiet garden.",
                 "risk": "Seek court favor through a bold gambit.",
                 "health": "Practice qigong at dawn.",
                 "network": "Visit a patron's salon.",
                 "rest": "Retreat to a quiet temple."},
    "habsburg": {"study": "Study languages and diplomacy at a small academy.",
                 "work": "Enter civil service or manage estates.",
                 "retire": "Retire to the countryside, tend affairs.",
                 "risk": "Speculate on new trade routes.",
                 "health": "Fence and ride daily.",
                 "network": "Host a small salon.",
                 "rest": "Take the waters at a spa."},
    "prehistoric":{"study": "Train in tracking, toolmaking, and star paths.",
                   "work": "Join the foraging and hunt rotations.",
                   "retire": "Step back from hunts; teach rituals.",
                   "risk": "Hunt alone at dusk.",
                   "health": "Train with weighted stones.",
                   "network": "Trade stories by the fire.",
                   "rest": "Meditate in the hot springs."},
}

def make_dynamic_options(era: str, band: str, stats: Stats) -> List[Option]:
    f = ERA_FLAVOR[era]
    opts: List[Option] = [
        Option(f["study"], {"knowledge": 2 if band != "infant" else 1, "health": -1 if band=="teen" else 0},
               {"study"}, set(), 0.0, 0.0, "dyn", template_id=f"dyn:{era}:study"),
        Option(f["network"], {"charisma": 2, "wealth": 1 if era in ("habsburg","modern") else 0},
               {"network"}, set(), 0.0, 0.0, "dyn", template_id=f"dyn:{era}:network"),
        Option(f["risk"], {"wealth": -2, "health": -1}, {"risk"}, set(), 0.08, 0.35, "dyn",
               template_id=f"dyn:{era}:risk"),
        Option(f["health"], {"health": 2}, {"health"}, set(), 0.0, 0.0, "dyn",
               template_id=f"dyn:{era}:health"),
        Option(f["rest"], {"health": 1, "karma": 1, "knowledge": -1 if band in ("teen","young_adult") else 0},
               {"rest"}, set(), 0.0, 0.0, "dyn", template_id=f"dyn:{era}:rest"),
    ]
    if band == "elder":
        for o in opts:
            if o.tags_set == {"risk"}:
                o.delta = {"wealth": -1, "health": -1}
                o.risk_death = 0.05
    return opts

def to_option_from_base(era: str, band: str, text: str, delta: Dict[str, int]) -> Option:
    t = text.lower()
    tags = set()
    if any(k in t for k in ["exam", "study", "copy", "science", "tutor", "project", "tool"]):
        tags.add("study")
    if any(k in t for k in ["ball", "salon", "meetup", "team", "patron", "donate"]):
        tags.add("network")
    if any(k in t for k in ["hunt", "walks", "qigong", "train", "exercise"]):
        tags.add("health")
    if any(k in t for k in ["bandit", "burns", "drought", "storm"]):
        tags.add("risk")
    swing = 0.2 if "risk" in tags else 0.0
    tid = f"base:{era}:{band}:{abs(hash(text))%100000}"
    return Option(text, dict(delta), tags, set(), 0.0, swing, "base", template_id=tid)

def bias_score(opt: Option, flags: Set[str]) -> int:
    return len(opt.tags_set & flags) + (1 if opt.requires and opt.requires.issubset(flags) else 0)

def personalize_option_text(opt: Option, age: int, band: str) -> Tuple[str, Dict[str, int]]:
    delta = dict(opt.delta)
    pre = f"At age {age}, "
    if band == "teen":
        if "rest" in opt.tags_set:    delta["health"] = delta.get("health", 0) + 1
        if "risk" in opt.tags_set:    delta["health"] = delta.get("health", 0) - 1
    elif band == "young_adult":
        if "study" in opt.tags_set:   delta["knowledge"] = delta.get("knowledge", 0) + 1
        if "work" in opt.tags_set:    delta["wealth"] = delta.get("wealth", 0) + 1
    elif band == "elder":
        if "health" in opt.tags_set:  delta["health"] = delta.get("health", 0) + 1
        if "risk" in opt.tags_set:    delta["health"] = delta.get("health", 0) - 1
    text = pre + opt.text
    return text, delta

def build_option_menu(era: str,
                      band: str,
                      age: int,
                      stats: Stats,
                      used_templates: Set[str],
                      flags: Set[str]) -> List[Option]:
    base_raw = ERA_AGE_EVENTS.get(era, {}).get(band, [])
    base_opts = []
    seen_texts = set()
    for text, delta in base_raw:
        if text in seen_texts:
            continue
        seen_texts.add(text)
        o = to_option_from_base(era, band, text, delta)
        if o.template_id in used_templates:
            continue
        base_opts.append(o)

    dyn_opts = [o for o in make_dynamic_options(era, band, stats) if o.template_id not in used_templates]
    all_opts = base_opts + dyn_opts
    if not all_opts:
        all_opts = [Option("Quiet year of routines.", {"karma": 1}, {"rest"}, set(), 0.0, 0.0, "dyn",
                           template_id=f"dyn:{era}:filler")]

    random.shuffle(all_opts)
    all_opts.sort(key=lambda o: bias_score(o, flags), reverse=True)

    menu: List[Option] = []
    seen = set()
    for o in all_opts:
        if o.template_id in seen:
            continue
        seen.add(o.template_id)
        txt, dd = personalize_option_text(o, age, band)
        menu.append(Option(txt, dd, set(o.tags_set), set(o.requires), o.risk_death, o.swing_prob, o.origin, o.template_id))
        if len(menu) == 3:
            break
    while len(menu) < 3:
        filler_id = f"dyn:{era}:filler:{age}:{len(menu)}"
        menu.append(Option(f"At age {age}, keep humble habits.", {"karma": 1}, {"rest"}, set(), 0.0, 0.0, "dyn", filler_id))
    return menu

# ------------- Milestones -------------

ERA_FLAVOR = ERA_FLAVOR  # (keep for clarity)

def build_milestone_menu(era: str, age: int, band: str) -> List[Option]:
    f = ERA_FLAVOR[era]
    if age in (7, 18, 24, 30):
        if age == 7:
            study = Option(f"At age {age}, " + f["study"], {"knowledge": 2, "health": 0},
                           {"study"}, set(), 0.0, 0.0, "milestone", template_id=f"mile:{age}:study:{era}")
            work_text = {
                "modern":  f"At age {age}, help with family chores and simple responsibilities.",
                "tang":    f"At age {age}, assist elders with errands and basic scripts.",
                "habsburg":f"At age {age}, shadow a steward for simple duties.",
                "prehistoric":f"At age {age}, gather berries and carry water for the camp.",
            }[era]
            work = Option(work_text, {"charisma": 1, "karma": 1, "health": -1},
                           {"work"}, set(), 0.00, 0.10, "milestone", template_id=f"mile:{age}:work:{era}")
        elif age in (18, 24):
            study = Option(f"At age {age}, " + f["study"],
                           {"knowledge": 3, "wealth": -1, "health": -1 if age==24 else 0},
                           {"study"}, set(), 0.0, 0.0, "milestone", template_id=f"mile:{age}:study:{era}")
            work  = Option(f"At age {age}, " + f["work"],
                           {"wealth": 2, "knowledge": 0, "health": -1},
                           {"work"}, set(), 0.04, 0.25, "milestone", template_id=f"mile:{age}:work:{era}")
        else:  # 30
            study = Option(f"At age {age}, " + f["study"], {"knowledge": 2, "wealth": -1},
                           {"study"}, set(), 0.0, 0.0, "milestone", template_id=f"mile:{age}:study:{era}")
            work  = Option(f"At age {age}, " + f["work"], {"wealth": 3, "health": -1},
                           {"work"}, set(), 0.05, 0.25, "milestone", template_id=f"mile:{age}:work:{era}")
        return [study, work]
    # 50
    work = Option(f"At age {age}, " + f["work"], {"wealth": 2, "health": -1},
                  {"work"}, set(), 0.04, 0.15, "milestone", template_id=f"mile:{age}:work:{era}")
    retire = Option(f"At age {age}, " + f["retire"], {"health": 2, "karma": 1, "wealth": -2},
                    {"retire"}, set(), 0.0, 0.0, "milestone", template_id=f"mile:{age}:retire:{era}")
    return [work, retire]

def next_unprocessed_milestone(age: int, processed: Set[int]) -> Optional[int]:
    future = [m for m in MILESTONES if m > age and m not in processed]
    return min(future) if future else None

def cap_age_step_to_milestone(age: int, step: int, processed: Set[int]) -> int:
    nxt = next_unprocessed_milestone(age, processed)
    if nxt is None:
        return step
    if age + step > nxt:
        return max(1, nxt - age)
    return step

# ------------- Random Variation & Endings -------------

def random_variation() -> Dict[str, int]:
    """Random ± adjustments applied after EACH player choice (not env)."""
    return {
        "health": random.randint(-3, 3),
        "wealth": random.randint(-3, 3),
        "knowledge": random.randint(-3, 3),
        "karma": random.randint(-3, 3),
        "charisma": random.randint(-3, 3),
    }

def check_special_endings(stats: Stats) -> Optional[str]:
    """Return ending text if any threshold is hit, else None."""
    # Negative endings at zero
    if stats.health == 0:
        return "Your life has come to an end. Ending: Death."
    if stats.wealth == 0:
        return "You lost everything. Ending: Bankruptcy."
    if stats.knowledge == 0:
        return "Your cognition collapses; you are sent to a psychiatric hospital for care. Ending: Dementia."
    if stats.charisma == 0:
        # Safe wording; avoid explicit self-harm details
        return "You are isolated and overwhelmed; the story ends in tragedy."
    if stats.karma == 0:
        return "Enemies come seeking revenge; you are killed."

    # Positive achievements: trigger immediately at >= ACHIEVEMENT_TARGET
    if stats.knowledge >= ACHIEVEMENT_TARGET:
        return "Unmatched brilliance; you receive a Nobel Genius Prize."
    if stats.wealth >= ACHIEVEMENT_TARGET:
        return "You reach the top of wealth and become the richest person in the world."
    if stats.health >= ACHIEVEMENT_TARGET:
        return "Vitality overflows; you become the chieftain of the undying."
    if stats.karma >= ACHIEVEMENT_TARGET:
        return "Virtue perfected; you ascend and become immortal."
    if stats.charisma >= ACHIEVEMENT_TARGET:
        return "Your charm radiates; you are adored by all."

    return None

# ------------- Risk Resolution & Env -------------

def resolve_outcome(opt: Option, stats: Stats) -> Tuple[Stats, bool, str, Dict[str,int]]:
    """
    Apply option delta with possible swing or death.
    Returns (new_stats, died, note, net_delta_applied_from_option)
    """
    note = ""
    net = dict(opt.delta)  # start with base option delta
    s = stats.apply(opt.delta)
    total_delta = sum(opt.delta.values())

    # Swing only possible when the overall option delta is negative
    if opt.swing_prob > 0 and total_delta < 0:
        if random.random() < opt.swing_prob:
            if random.random() < 0.5:
                swing = {"knowledge": 1, "karma": 1}
                s = s.apply(swing)
                net = add_delta(net, swing)
                note = "(Against the odds, you grow from the setback.)"
            else:
                swing = {"health": -1, "karma": -1}
                s = s.apply(swing)
                net = add_delta(net, swing)
                note = "(The setback deepens into a rough patch.)"

    # Death risk
    death_prob = opt.risk_death
    if "risk" in opt.tags_set and s.health <= 10:
        death_prob = min(1.0, death_prob + 0.10)
    died = (random.random() < death_prob)
    if died:
        # Set health to 0 as an additional consequence (to trigger ending check)
        death_delta = {"health": -s.health}
        s = s.apply(death_delta)
        net = add_delta(net, death_delta)
        note = (note + " " if note else "") + "[You collapse.]"

    return s, died, note, net

def maybe_env_trigger(era_key: str,
                      age: int,
                      used_triggers: Set[Tuple[str, str, str]]) -> Optional[Tuple[str, Dict[str, int]]]:
    if random.random() >= ENV_TRIGGER_PROB:
        return None
    band = current_band(age)
    pool = ENV_TRIGGERS.get(era_key, {}).get(band, [])
    if not pool:
        return None
    candidates = [(t, d) for (t, d) in pool if (era_key, band, t) not in used_triggers]
    if not candidates:
        return None
    return pick(candidates)

def random_age_step(age: int) -> int:
    lo, hi = AGE_STEP_MIN_MAX
    if age <= 2:
        hi = max(2, hi - 2)
    return random.randint(lo, hi)

# ------------- UI Helpers (with clear effect preview) -------------

def choose(title: str, options: List[Tuple[str, str]]) -> str:
    print("\n" + title)
    for idx, (k, label) in enumerate(options, start=1):
        print("  {0}) {1}".format(idx, label))
    while True:
        ans = input("Pick 1..{0}: ".format(len(options))).strip()
        if ans.isdigit():
            i = int(ans)
            if 1 <= i <= len(options):
                return options[i - 1][0]
        print("Invalid choice, try again.")

def choose_from_options(menu: List[Option], allow_rift: bool = True) -> Option:
    # Show preview of deltas & risk/swing BEFORE choosing
    for idx, o in enumerate(menu, start=1):
        total = sum(o.delta.values())
        hint = " + " if total > 0 else (" - " if total < 0 else " ~ ")
        preview = make_preview_text(o)
        print(f"  {idx}){hint}{o.text}")
        print(f"      Δ preview → {preview}")
    prompt = "Choose 1..{0}{1}: ".format(len(menu), " (or 'r' for time rift)" if allow_rift else "")
    while True:
        ans = input(prompt).strip().lower()
        if allow_rift and ans == "r":
            return Option("__RIFT__", {}, set(), set(), 0.0, 0.0, "dyn", template_id="__RIFT__")
        if ans.isdigit():
            i = int(ans)
            if 1 <= i <= len(menu):
                return menu[i - 1]
        print("Invalid choice, try again.")

def print_stats(stats: Stats, age: int):
    print("Age: {0}   Stats: {1}".format(age, stats.pretty()))

# ------------- Game Loop -------------

def play(seed: int = None):
    if seed is not None:
        random.seed(seed)

    # Login/Register
    auth_flow()

    print("=== Life Restart Simulator (CLI) ===\n")

    birth = choose("1) Choose your birth status", BIRTHS)
    nation = choose("2) Choose your nationality", NATIONALITIES)
    era = choose("3) Choose your starting era", ERAS)

    stats = starting_stats(birth)
    age = 0
    flags: Set[str] = set()
    used_templates: Set[str] = set()
    used_trigs: Set[Tuple[str, str, str]] = set()
    processed_milestones: Set[int] = set()
    log: List[str] = []

    log.append("You are reborn ({0}) in {1} during {2} at age {3}.".format(
        birth.upper(), label_of(NATIONALITIES, nation), label_of(ERAS, era), age
    ))
    print_stats(stats, age)

    chapter = 0
    while chapter < CHAPTER_LIMIT and age < MAX_AGE:
        chapter += 1
        band = current_band(age)
        print("\n--- Chapter {0}: {1} years old ({2}) ---".format(chapter, age, band))

        # Milestone?
        if age in MILESTONES and age not in processed_milestones:
            menu = build_milestone_menu(era, age, band)
            opt = choose_from_options(menu, allow_rift=False)
        else:
            menu = build_option_menu(era, band, age, stats, used_templates, flags)
            opt = choose_from_options(menu, allow_rift=True)
            if opt.template_id == "__RIFT__":
                era = open_time_rift(era)
                band = current_band(age)
                menu = build_option_menu(era, band, age, stats, used_templates, flags)
                opt = pick(menu)
                print("(Auto-picked after rift) {0}".format(opt.text))

        # Resolve base outcome (risk/swing) and report net effect
        new_stats, _died_flag, note, net_option = resolve_outcome(opt, stats)

        # Apply random variation (ALWAYS after player's choice) & show
        rnd = random_variation()
        new_stats = new_stats.apply(rnd)
        net_total = add_delta(net_option, rnd)

        # Full breakdown for the player
        print(opt.text)
        if note:
            print("  Event note:", note)
        print("  Result →", fmt_delta(net_option))
        print("  Random variation →", fmt_delta(rnd))
        print("  Total this turn →", fmt_delta(net_total))

        stats = new_stats
        print_stats(stats, age)

        # Mark usage/flags & milestone record
        if opt.origin == "milestone":
            processed_milestones.add(age)
        if opt.template_id != "__RIFT__":
            used_templates.add(opt.template_id)
        flags |= set(opt.tags_set)
        log.append("[age {0}] {1} | result {2} | rnd {3} | total {4} -> {5}".format(
            age, opt.text, fmt_delta(net_option), fmt_delta(rnd), fmt_delta(net_total), stats.pretty()
        ))

        # Special endings check (immediate)
        ending = check_special_endings(stats)
        if ending:
            print("\n=== Special Ending ===")
            print(ending)
            print("\n--- Life Log ---")
            for line in log:
                print("* " + line)
            return 0

        # Environment trigger (report impact separately)
        trig = maybe_env_trigger(era, age, used_trigs)
        if trig:
            t_text, t_delta = trig
            stats = stats.apply(t_delta)
            used_trigs.add((era, band, t_text))
            print("\nEnvironment:", t_text)
            print("  Environment impact →", fmt_delta(t_delta))
            print_stats(stats, age)
            log.append("[age {0}] ENV {1} | impact {2} -> {3}".format(
                age, t_text, fmt_delta(t_delta), stats.pretty()
            ))
            ending2 = check_special_endings(stats)
            if ending2:
                print("\n=== Special Ending ===")
                print(ending2)
                print("\n--- Life Log ---")
                for line in log:
                    print("* " + line)
                return 0

        # Age advance with milestone capping
        step = random_age_step(age)
        step = cap_age_step_to_milestone(age, step, processed_milestones)
        age = min(MAX_AGE, age + step)
        print("Time passes: +{0} years. Age is now {1}.".format(step, age))

        if age >= MAX_AGE:
            print("\n=== Final Ending ===")
            print("You lived a brilliant life.")
            print("\n--- Life Log ---")
            for line in log:
                print("* " + line)
            return 0

    # Fallback (shouldn't reach)
    print("\n=== Final Page ===")
    print("Era at rest: {0}   Nation: {1}".format(label_of(ERAS, era), label_of(NATIONALITIES, nation)))
    print_stats(stats, age)
    print("\n" + ending_for(stats, era))
    print("\n--- Life Log ---")
    for line in log:
        print("* " + line)
    return 0

def main(argv: List[str]) -> int:
    if len(argv) >= 2 and argv[1].isdigit():
        seed = int(argv[1])
    else:
        seed = None
    return play(seed=seed)

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
