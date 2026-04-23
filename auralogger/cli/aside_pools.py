"""CLI aside pools and pickers — parity with node/src/cli/utility/aside-pools.ts."""

from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Literal, TypedDict

from auralogger.utils.recovery_messages import ENV_RECOVERY_HINT_PLAIN

AsideTier = Literal["common", "rare", "legendary"]


class AsideEntry(TypedDict, total=False):
    emoji: str
    line: str
    tier: AsideTier
    weight: float


class TieredAsidePools(TypedDict):
    common: List[AsideEntry]
    rare: List[AsideEntry]
    legendary: List[AsideEntry]


DEFAULT_SILENCE_ASIDE_CHANCE = 0.15

ErrorAsideKind = Literal["auth-env", "network", "logic", "generic"]


def format_aside_template(template: str, values: Dict[str, Any]) -> str:
    def repl(m: Any) -> str:
        key = m.group(1)
        return str(values.get(key, ""))

    return re.sub(r"\{\{(\w+)\}\}", repl, template)


def pick_aside(pool: List[AsideEntry]) -> AsideEntry:
    return pool[random.randrange(len(pool))]


def pick_tiered_aside(pools: TieredAsidePools) -> AsideEntry:
    r = random.random()
    leg = pools["legendary"]
    rare = pools["rare"]
    common = pools["common"]
    if len(leg) > 0 and r < 0.02:
        return pick_aside(leg)
    if len(rare) > 0 and r < 0.15:
        return pick_aside(rare)
    if len(common) > 0:
        return pick_aside(common)
    if len(rare) > 0:
        return pick_aside(rare)
    return pick_aside(leg)


def classify_error_for_aside(message: str) -> ErrorAsideKind:
    m = message.lower()
    if (
        "network" in m
        or "vpn" in m
        or "wi-fi" in m
        or "wi fi" in m
        or "reach auralogger" in m
        or "can't reach" in m
        or "unable to reach" in m
        or "econnrefused" in m
        or "fetch failed" in m
        or "socket" in m
        or "timed out" in m
        or "timeout" in m
        or "connection" in m
        or "tunnel" in m
        or "dns" in m
    ):
        return "network"
    if (
        "token" in m
        or "secret" in m
        or "auth" in m
        or "401" in m
        or "403" in m
        or ".env" in m
        or "credential" in m
        or "unauthorized" in m
        or "forbidden" in m
        or "auralogger_project" in m
        or "user_secret" in m
    ):
        return "auth-env"
    if (
        "json" in m
        or "parse" in m
        or "invalid" in m
        or "filter" in m
        or "expected" in m
        or "unknown filter" in m
        or "garbled" in m
    ):
        return "logic"
    return "generic"


GENERIC_SPICE_DEADPOOL_ASIDES: List[AsideEntry] = [
    {"emoji": "💀", "line": "Deadpool: Not your best work. We move."},
    {"emoji": "💀", "line": "Deadpool: I've seen worse. Not today though."},
    {"emoji": "💀", "line": "Deadpool: You're learning. Slowly. Painfully."},
]

WOLVERINE_NUDGE_ASIDES: List[AsideEntry] = [
    {"emoji": "🐺", "line": "Wolverine: Focus."},
    {"emoji": "🐺", "line": "Wolverine: Read properly."},
    {"emoji": "🐺", "line": "Wolverine: Again. Carefully."},
]

FATAL_FIRST_FAIL_GENERIC_TONY_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🦾",
        "line": "Tony: That's not valid — fix the command or the input, then rerun.",
    },
    {"emoji": "🦾", "line": "Tony: Red line's the truth. Adjust, rerun, we're good."},
]

FATAL_FIRST_FAIL_AUTH_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🦾",
        "line": (
            "Tony: Auth blew up — token, user secret, or .env in the wrong place. "
            "Pick one, fix it, rerun. Not a personality test."
        ),
    },
    {
        "emoji": "💀",
        "line": (
            "Deadpool: Server looked at your creds and went 'nope.' Sync .env with reality "
            "— or run init like a grown-up."
        ),
    },
    {
        "emoji": "🐺",
        "line": (
            "Wolverine: 401/403 isn't moody — it's wrong secret or wrong token. "
            "Fix .env, same cwd you run commands from."
        ),
    },
]

FATAL_FIRST_FAIL_NETWORK_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🐺",
        "line": (
            "Wolverine: Fetch died — Wi‑Fi, VPN, firewall, or you're not even in the "
            "project folder. Hunt in that order."
        ),
    },
    {
        "emoji": "🦾",
        "line": (
            "Tony: Relax — can't reach the API. Toggle VPN, check proxy, confirm you're "
            "online. Then we talk .env."
        ),
    },
    {
        "emoji": "💀",
        "line": (
            "Deadpool: The internet ghosted you. Or Auralogger did. Either way — "
            "network first, blame the code second."
        ),
    },
    {
        "emoji": "🧪",
        "line": (
            "Banner: Connection failed — rule out network, then AURALOGGER_WS_URL / API URL "
            "overrides. Science, not vibes."
        ),
    },
]

FATAL_FIRST_FAIL_LOGIC_ASIDES: List[AsideEntry] = [
    {"emoji": "🧪", "line": "Banner: Logic/input — read the line above, then fix the shape."},
    {"emoji": "💀", "line": "Deadpool: Cool, it broke. Fix filters/JSON, rerun."},
]

FATAL_ESCALATION_WOLVERINE_ASIDES: List[AsideEntry] = [
    {"emoji": "🐺", "line": "Wolverine: Same mistake. Slow down."},
    {"emoji": "🐺", "line": "Wolverine: Again? Read twice, type once."},
]

FATAL_ESCALATION_DEADPOOL_ASIDES: List[AsideEntry] = [
    {"emoji": "💀", "line": "Deadpool: Oh wow we're doing this again."},
    {"emoji": "💀", "line": "Deadpool: Déjà vu, but worse."},
]

FATAL_ESCALATION_HULK_ASIDES: List[AsideEntry] = [
    {"emoji": "💚", "line": "Hulk: STOP BREAKING."},
    {"emoji": "💚", "line": "Hulk: USER. FIX. COMMAND."},
]

FATAL_MULTI_CHAIN_ASIDES: List[AsideEntry] = [
    {
        "emoji": "💀",
        "line": (
            "Deadpool: Still nothing.\nWolverine: Then nothing ran.\nDeadpool: Or "
            "everything died.\nWolverine: Fix it."
        ),
    },
    {
        "emoji": "💀",
        "line": (
            "Deadpool: He's about to rerun without fixing it.\nWolverine: Don't.\n"
            "Deadpool: He did it.\nWolverine: Of course."
        ),
    },
    {
        "emoji": "🦾",
        "line": (
            "Tony: It works.\nDeadpool: Suspicious.\nTony: It's correct.\n"
            "Deadpool: For now."
        ),
    },
    {
        "emoji": "💚",
        "line": "Banner: Something's wrong.\nHulk: SMASH.\nBanner: Not yet.\nHulk: SOON.",
    },
]


def pick_adaptive_fatal_aside(consecutive_failures: int, error_message: str) -> AsideEntry:
    if consecutive_failures >= 4 and random.random() < 0.22:
        return pick_aside(FATAL_MULTI_CHAIN_ASIDES)
    if consecutive_failures >= 5 and random.random() < 0.48:
        return pick_aside(FATAL_ESCALATION_HULK_ASIDES)
    if consecutive_failures >= 3:
        return pick_aside(FATAL_ESCALATION_DEADPOOL_ASIDES)
    if consecutive_failures == 2:
        return pick_aside(FATAL_ESCALATION_WOLVERINE_ASIDES)

    kind = classify_error_for_aside(error_message)
    if kind == "network":
        return pick_aside(FATAL_FIRST_FAIL_NETWORK_ASIDES)
    if kind == "auth-env":
        return pick_aside(FATAL_FIRST_FAIL_AUTH_ASIDES)
    if kind == "logic":
        return pick_aside(FATAL_FIRST_FAIL_LOGIC_ASIDES)
    return pick_aside(FATAL_FIRST_FAIL_GENERIC_TONY_ASIDES)


BIN_USAGE_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🕷️",
        "line": (
            "Peter: Pick a command, dude — init if you're setting things up, get-logs if "
            "you're hunting past mistakes, *-check if you're paranoid (valid)."
        ),
    },
    {
        "emoji": "💀",
        "line": (
            "Deadpool: Alright, press a button. Any button. Preferably init if you have "
            "no idea what you're doing (which… statistically, you don't)."
        ),
    },
    {
        "emoji": "🦾",
        "line": (
            "Tony: Let's not freestyle this. init sets you up, get-logs shows your mistakes, "
            "*-check tells you if things are actually working. Pick a command. Preferably "
            "the right one this time."
        ),
    },
]

BIN_USAGE_RARE_MULTI_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🦾",
        "line": (
            "Tony: It works.\nDeadpool: For once.\nTony: It usually works.\n"
            "Deadpool: Sure it does."
        ),
    },
    {
        "emoji": "🦾",
        "line": (
            "Tony: It works.\nDeadpool: Suspicious.\nTony: It's correct.\n"
            "Deadpool: For now."
        ),
    },
]

BIN_UNKNOWN_COMMAND_TEMPLATES: List[AsideEntry] = [
    {"emoji": "🐺", "line": 'Wolverine: "{{cmd}}" isn\'t a command. Read the list.'},
    {"emoji": "🦾", "line": 'Tony: "{{cmd}}" — not a thing. Copy a real command from the list.'},
    {"emoji": "💀", "line": 'Deadpool: "{{cmd}}" — bold, wrong, we\'re taking notes.'},
]

BIN_USAGE_LEGENDARY_ASIDES: List[AsideEntry] = [
    {"emoji": "💚", "line": "Hulk: PICK. COMMAND."},
]

CLI_VETERAN_USAGE_ASIDES: List[AsideEntry] = [
    {"emoji": "🦾", "line": "Tony: Back again. Good."},
    {"emoji": "💀", "line": "Deadpool: Regular. Cute."},
]

ENV_SETUP_RECOVERY_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🦾",
        "line": (
            "Tony: .env lives where you run this — not three folders up, not your Downloads. "
            "init hands you the cheat sheet."
        ),
    },
    {
        "emoji": "🐺",
        "line": (
            "Wolverine: Wrong cwd, empty .env, drunk paste — one of those. Fix it, init if "
            "you're lost, move on."
        ),
    },
    {
        "emoji": "💀",
        "line": (
            "Deadpool: npx auralogger init is the dotenv greatest-hits album. Same repo root "
            "you actually use. You're welcome."
        ),
    },
    {
        "emoji": "💀",
        "line": (
            "Deadpool: If your secret's in the clipboard and not in .env, that's not 'agile' "
            "— that's chaos."
        ),
    },
    {
        "emoji": "🦾",
        "line": (
            "Tony: Matching tokens, real .env, cwd that makes sense. init exists because "
            "READMEs are decorative."
        ),
    },
]

INIT_REPEAT_INTENT_ASIDES: List[AsideEntry] = [
    {"emoji": "💀", "line": "Deadpool: Init again? Didn't trust yourself the first time?"},
    {"emoji": "🦾", "line": "Tony: Back for round two — bring the right token."},
]

INIT_WELCOME_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🎬",
        "line": (
            "Tony: Welcome to setup. Answer the prompts. Yes, all of them. This isn't "
            "optional character development."
        ),
    },
    {
        "emoji": "🎬",
        "line": (
            "Tony: Welcome to setup. Answer the prompts. Don't skip ahead. This isn't a "
            "YouTube tutorial."
        ),
    },
    {
        "emoji": "💀",
        "line": (
            "Deadpool: We're about to store secrets. Not your feelings — actual secrets. "
            "Try not to leak them this time."
        ),
    },
]

INIT_SESSION_TONY_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🦾",
        "line": (
            "Tony: Session's valid — next step's below. Relax: browser never gets the user "
            "secret. Don't get creative."
        ),
    },
]

INIT_STRANGE_TOKEN_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🔮",
        "line": (
            "Strange: Token's in env, session isn't — one proj_auth call. Don't overthink it."
        ),
    },
]

PROMPT_MISSING_CREDENTIAL_TEMPLATES: List[AsideEntry] = [
    {
        "emoji": "🦾",
        "line": (
            "Tony: No {{envKey}} in env — paste next, then slam it in .env or run "
            "npx auralogger init. Server-check will love you."
        ),
    },
    {
        "emoji": "🕷️",
        "line": (
            "Peter: {{envKey}} ghosted us — paste below, .env or init, future-you says thanks."
        ),
    },
    {
        "emoji": "💀",
        "line": (
            "Deadpool: {{envKey}} MIA — type it, cage it in .env, or init holds your hand. "
            "I'm not HR."
        ),
    },
    {
        "emoji": "🐺",
        "line": (
            "Wolverine: {{envKey}} missing — you knew this'd prompt. .env or init, then rerun."
        ),
    },
]

INIT_CURTAIN_TONY_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🎬",
        "line": (
            "Tony: Init's on the board. Optional boss fight: auralogger server-check — "
            "prove the wire's real."
        ),
    },
]

INIT_ALREADY_STRANGE_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🔮",
        "line": (
            "Strange: Everything you need is already in this shell. Don't overthink it. "
            "Just execute."
        ),
    },
]

INIT_ALREADY_LOKI_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🐍",
        "line": (
            "Loki: Need a new session? Clear it and run init again. Relax, it's a reset — "
            "not a crime scene cleanup."
        ),
    },
]

INIT_ALREADY_STEVE_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🛡️",
        "line": (
            "Steve: When you're ready — auralogger server-check. Verify the pipe; don't just vibe."
        ),
    },
]

GET_LOGS_EMPTY_ASIDES: List[AsideEntry] = [
    {
        "emoji": "💀",
        "line": (
            "Deadpool: Zero logs — nothing happened or everything broke quietly. Both annoying."
        ),
    },
    {
        "emoji": "🐺",
        "line": (
            "Wolverine: No logs. Either nothing ran… or nothing worked. Either way — fix it."
        ),
    },
    {"emoji": "🧪", "line": "Banner: No rows — loosen filters or confirm the app actually logs."},
]

GET_LOGS_SUCCESS_TEMPLATES: List[AsideEntry] = [
    {
        "emoji": "🦾",
        "line": (
            "Tony: {{n}} logs — there's your paper trail. Read it before you blame the network."
        ),
    },
    {"emoji": "💀", "line": "Deadpool: {{n}} logs. That's a lot of evidence against you."},
    {"emoji": "🐺", "line": "Wolverine: {{n}} logs. Stop scrolling, start fixing."},
]

GET_LOGS_STYLES_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🦾",
        "line": (
            "Tony: No styles? Borrowed them for this run. Toss in .env later if you care about looks."
        ),
    },
    {
        "emoji": "💀",
        "line": "Deadpool: We stole some colors for this run. Don't get attached.",
    },
]

GET_LOGS_SKIPPED_SETUP_INTENT_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🦾",
        "line": "Tony: No token, no setup — and you still ran this. Bold. Fix it.",
    },
    {
        "emoji": "💀",
        "line": "Deadpool: Skipped setup and expected magic. I respect the confidence.",
    },
]

GET_LOGS_OPEN_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🦾",
        "line": "Tony: Pulling logs. Credentials are handled — don't do anything creative.",
    },
    {
        "emoji": "💀",
        "line": (
            "Deadpool: Secure request incoming. Please don't leak anything in chat this time."
        ),
    },
]

GET_LOGS_DEADPOOL_SCROLL_ASIDES: List[AsideEntry] = [
    {"emoji": "💀", "line": "Deadpool: Still scrolling? That's not debugging — that's avoidance."},
    {
        "emoji": "💀",
        "line": "Deadpool: 200 lines deep and no clue? Consistency, I'll give you that.",
    },
]

SERVER_CHECK_OPEN_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🦾",
        "line": (
            "Tony: Opening the pipe—secret stays server-side, token rides the URL, don't panic unless it stalls."
        ),
    },
    {
        "emoji": "🐺",
        "line": (
            "Wolverine: Opening pipe. VPN, firewall, wrong env — pick your villain if it dies."
        ),
    },
    {
        "emoji": "💀",
        "line": (
            "Deadpool: Server WebSocket o'clock. If it fails, it's almost never 'mysterious magic.'"
        ),
    },
]

SERVER_CHECK_SUCCESS_THOR_ASIDES: List[AsideEntry] = [
    {"emoji": "⚡", "line": "Thor: Log sent. Dashboard empty? Refresh."},
    {
        "emoji": "🦾",
        "line": (
            "Tony: Relax — socket's fine. Your UI just needs a refresh. Not everything's a crisis."
        ),
    },
]

SERVER_CHECK_FAIL_WOLVERINE_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🐺",
        "line": (
            "Wolverine: If it timed out, something's blocking it. Find it. Fix it. Move on."
        ),
    },
]

CHECK_RETRY_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🦾",
        "line": "Tony: Glitches happen—hit retry before the speeches.",
    },
    {
        "emoji": "💀",
        "line": "Deadpool: Retry arc unlocked. Same plan, less panic.",
    },
    {
        "emoji": "🐺",
        "line": "Wolverine: Breathe. Retry. Then decide what's broken.",
    },
]

CLIENT_CHECK_START_PETER_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🕷️",
        "line": "Peter: This is how browsers talk. No secret. Just the token. Simple, safe, done.",
    },
    {
        "emoji": "🕷️",
        "line": (
            "Peter: Browser tunnel—token in the URL, no Bearer, just like a real tab."
        ),
    },
]

CLIENT_CHECK_SUCCESS_ASIDES: List[AsideEntry] = [
    {"emoji": "🐺", "line": "Wolverine: It works here. Your app should match it. No excuses."},
    {"emoji": "💀", "line": "Deadpool: This passed. Your app didn't. That's not a coincidence."},
]

TEST_SERVERLOG_START_BANNER_ASIDES: List[AsideEntry] = [
    {
        "emoji": "💚",
        "line": (
            "Banner: Sending real logs through the production path. This is the signal, "
            "not a simulation."
        ),
    },
    {
        "emoji": "💚",
        "line": (
            "Banner: Same pipeline as production. If this fails, the issue is real."
        ),
    },
]

TEST_SERVERLOG_SUCCESS_MAIN_ASIDES: List[AsideEntry] = [
    {
        "emoji": "🦾",
        "line": "Tony: Logs landed. System's working. If something's wrong, it's upstream.",
    },
    {
        "emoji": "💀",
        "line": "Deadpool: Logs are in. If you still can't find the bug… that's a talent.",
    },
]


def pick_test_serverlog_success_aside() -> AsideEntry:
    if random.random() < 0.05:
        return {"emoji": "💚", "line": "Hulk: LOGS SMASH. WORK GOOD."}
    return pick_aside(TEST_SERVERLOG_SUCCESS_MAIN_ASIDES)
