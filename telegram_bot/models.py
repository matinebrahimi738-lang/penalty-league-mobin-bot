"""
Data models, enums, and dataclasses for the PLM bot.
These are pure Python objects — no ORM, just structured types.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class RPSChoice(str, Enum):
    """Rock-Paper-Scissors choices."""
    ROCK = "rock"
    PAPER = "paper"
    SCISSORS = "scissors"


class Direction(str, Enum):
    """Penalty kick / save direction."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class MatchStatus(str, Enum):
    """Lifecycle states of a match."""
    PENDING = "pending"           # Created, waiting for players to join
    RPS = "rps"                   # Rock-Paper-Scissors phase
    IN_PROGRESS = "in_progress"   # Penalty rounds ongoing
    SUDDEN_DEATH = "sudden_death" # Tie-breaker rounds
    FINISHED = "finished"         # Match completed
    CANCELLED = "cancelled"       # Admin cancelled


class RoundResult(str, Enum):
    """Outcome of a single penalty round."""
    GOAL = "goal"
    SAVE = "save"
    PENDING = "pending"


class RPSResult(str, Enum):
    """Outcome of the RPS phase."""
    PLAYER1_WINS = "player1_wins"
    PLAYER2_WINS = "player2_wins"
    DRAW = "draw"


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Player:
    """Represents a registered player."""
    id: int                           # Telegram user ID
    username: str
    full_name: str
    team_name: str
    team_flag: str                    # Emoji flag
    matches_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    goals_scored: int = 0
    goals_missed: int = 0
    saves_made: int = 0
    win_streak: int = 0
    current_streak: int = 0
    registered_at: float = field(default_factory=time.time)
    is_active: bool = True

    @property
    def win_rate(self) -> float:
        if self.matches_played == 0:
            return 0.0
        return round((self.wins / self.matches_played) * 100, 1)

    @property
    def display_name(self) -> str:
        return f"{self.team_flag} {self.team_name}"

    @property
    def points(self) -> int:
        """League points: 3 per win, 1 per draw."""
        return (self.wins * 3) + self.draws


@dataclass
class Admin:
    """Represents a bot administrator."""
    id: int          # Telegram user ID
    username: str
    full_name: str
    added_at: float = field(default_factory=time.time)
    is_super: bool = False


@dataclass
class Round:
    """Represents a single penalty round within a match."""
    round_number: int
    shooter_id: int
    goalkeeper_id: int
    shooter_direction: Optional[Direction] = None
    goalkeeper_direction: Optional[Direction] = None
    result: RoundResult = RoundResult.PENDING
    is_sudden_death: bool = False
    completed_at: Optional[float] = None

    @property
    def is_complete(self) -> bool:
        return (
            self.shooter_direction is not None
            and self.goalkeeper_direction is not None
        )

    def evaluate(self) -> RoundResult:
        """Determine result: same direction = SAVE, different = GOAL."""
        if not self.is_complete:
            return RoundResult.PENDING
        if self.shooter_direction == self.goalkeeper_direction:
            return RoundResult.SAVE
        return RoundResult.GOAL


@dataclass
class Match:
    """Represents a full penalty shootout match."""
    id: int
    player1_id: int
    player2_id: int
    player1_team: str
    player2_team: str
    player1_flag: str
    player2_flag: str
    channel_id: str
    status: MatchStatus = MatchStatus.PENDING
    max_rounds: int = 5

    # RPS phase
    player1_rps: Optional[RPSChoice] = None
    player2_rps: Optional[RPSChoice] = None
    rps_winner_id: Optional[int] = None          # Who shoots first

    # Match progress
    current_round: int = 0
    player1_score: int = 0
    player2_score: int = 0
    winner_id: Optional[int] = None

    # Telegram message IDs for editing live messages
    channel_message_id: Optional[int] = None
    player1_message_id: Optional[int] = None
    player2_message_id: Optional[int] = None

    # Timing
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

    # Rounds list (populated from DB)
    rounds: List[Round] = field(default_factory=list)

    # Anti-cheat: track pending round choices
    _current_shooter_choice: Optional[Direction] = field(default=None, repr=False)
    _current_gk_choice: Optional[Direction] = field(default=None, repr=False)

    @property
    def is_active(self) -> bool:
        return self.status in (
            MatchStatus.RPS,
            MatchStatus.IN_PROGRESS,
            MatchStatus.SUDDEN_DEATH,
        )

    @property
    def current_shooter_id(self) -> Optional[int]:
        """Who shoots in the current round (alternates)."""
        if not self.rps_winner_id:
            return None
        # RPS winner shoots in odd rounds (1, 3, 5...), loser in even
        if self.current_round % 2 == 1:
            return self.rps_winner_id
        return (
            self.player2_id
            if self.rps_winner_id == self.player1_id
            else self.player1_id
        )

    @property
    def current_goalkeeper_id(self) -> Optional[int]:
        shooter = self.current_shooter_id
        if shooter is None:
            return None
        return (
            self.player2_id if shooter == self.player1_id else self.player1_id
        )

    def get_form(self, player_id: int) -> str:
        """Generate FORM string: 🟢 = goal scored, 🔴 = saved, ⚪ = not played."""
        circles = []
        for r in self.rounds:
            if r.result == RoundResult.PENDING:
                circles.append("⚪")
            elif r.shooter_id == player_id:
                circles.append("🟢" if r.result == RoundResult.GOAL else "🔴")
            else:
                # This player was goalkeeper
                circles.append("🔴" if r.result == RoundResult.SAVE else "🟢")
        # Pad to max_rounds
        while len(circles) < self.max_rounds:
            circles.append("⚪")
        return "".join(circles[:self.max_rounds])

    def can_player1_win_early(self) -> bool:
        """Check if player1 has mathematically already won."""
        remaining = self.max_rounds - self.current_round
        return self.player1_score > self.player2_score + remaining

    def can_player2_win_early(self) -> bool:
        remaining = self.max_rounds - self.current_round
        return self.player2_score > self.player1_score + remaining


@dataclass
class LeagueEntry:
    """A single row in the league table."""
    player_id: int
    team_name: str
    team_flag: str
    full_name: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def rank_key(self):
        """Sort key for league ranking (desc)."""
        return (self.points, self.goal_difference, self.goals_for, self.wins)


@dataclass
class Statistics:
    """Aggregated statistics for a player."""
    player_id: int
    total_matches: int = 0
    total_wins: int = 0
    total_losses: int = 0
    total_draws: int = 0
    total_goals_scored: int = 0
    total_goals_conceded: int = 0
    total_saves: int = 0
    total_shots: int = 0
    best_win_streak: int = 0
    current_win_streak: int = 0
    last_match_result: Optional[str] = None


@dataclass
class Setting:
    """A bot-wide key-value setting."""
    key: str
    value: str
    updated_at: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════════════════════
# RPS LOGIC
# ═══════════════════════════════════════════════════════════════════════════════

_RPS_WINS: Dict[RPSChoice, RPSChoice] = {
    RPSChoice.ROCK: RPSChoice.SCISSORS,
    RPSChoice.SCISSORS: RPSChoice.PAPER,
    RPSChoice.PAPER: RPSChoice.ROCK,
}


def evaluate_rps(c1: RPSChoice, c2: RPSChoice) -> RPSResult:
    """Return who wins the RPS round."""
    if c1 == c2:
        return RPSResult.DRAW
    if _RPS_WINS[c1] == c2:
        return RPSResult.PLAYER1_WINS
    return RPSResult.PLAYER2_WINS


# Country teams available for selection
AVAILABLE_TEAMS = [
    ("🇮🇷", "Iran"),
    ("🇧🇷", "Brazil"),
    ("🇩🇪", "Germany"),
    ("🇫🇷", "France"),
    ("🇦🇷", "Argentina"),
    ("🇪🇸", "Spain"),
    ("🇵🇹", "Portugal"),
    ("🇮🇹", "Italy"),
    ("🇬🇧", "England"),
    ("🇳🇱", "Netherlands"),
    ("🇧🇪", "Belgium"),
    ("🇭🇷", "Croatia"),
    ("🇺🇾", "Uruguay"),
    ("🇯🇵", "Japan"),
    ("🇰🇷", "South Korea"),
    ("🇲🇦", "Morocco"),
    ("🇸🇳", "Senegal"),
    ("🇬🇭", "Ghana"),
    ("🇳🇬", "Nigeria"),
    ("🇺🇸", "USA"),
    ("🇲🇽", "Mexico"),
    ("🇨🇴", "Colombia"),
    ("🇨🇱", "Chile"),
    ("🇵🇪", "Peru"),
    ("🇩🇰", "Denmark"),
    ("🇸🇪", "Sweden"),
    ("🇨🇭", "Switzerland"),
    ("🇵🇱", "Poland"),
    ("🇨🇿", "Czech Republic"),
    ("🇷🇸", "Serbia"),
    ("🇹🇷", "Turkey"),
    ("🇦🇺", "Australia"),
    ("🇯🇴", "Jordan"),
    ("🇭🇰", "Hong Kong"),
    ("🇸🇦", "Saudi Arabia"),
    ("🇶🇦", "Qatar"),
    ("🇪🇬", "Egypt"),
    ("🇨🇲", "Cameroon"),
    ("🇨🇦", "Canada"),
    ("🇧🇴", "Bolivia"),
]
