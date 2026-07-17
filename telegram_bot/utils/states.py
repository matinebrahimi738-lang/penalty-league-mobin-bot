"""
FSM State Groups for the PLM bot.
Every multi-step conversation flow has its own StatesGroup.
"""

from aiogram.fsm.state import State, StatesGroup


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN FLOWS
# ─────────────────────────────────────────────────────────────────────────────

class CreateMatchStates(StatesGroup):
    """Admin flow: create a new match."""
    waiting_player1    = State()
    waiting_player2    = State()
    waiting_channel    = State()
    confirm            = State()


class AddPlayerStates(StatesGroup):
    """Admin flow: manually add a player."""
    waiting_user_id    = State()
    waiting_team       = State()
    confirm            = State()


class AddAdminStates(StatesGroup):
    """Admin flow: promote a user to admin."""
    waiting_user_id    = State()
    confirm            = State()


class BroadcastStates(StatesGroup):
    """Admin flow: send broadcast to all players."""
    waiting_message    = State()
    confirm            = State()


class SettingsStates(StatesGroup):
    """Admin flow: change bot settings."""
    waiting_key        = State()
    waiting_value      = State()


# ─────────────────────────────────────────────────────────────────────────────
# PLAYER REGISTRATION FLOW
# ─────────────────────────────────────────────────────────────────────────────

class RegisterStates(StatesGroup):
    """New player registration."""
    waiting_team       = State()
    confirm            = State()


# ─────────────────────────────────────────────────────────────────────────────
# MATCH FLOW
# ─────────────────────────────────────────────────────────────────────────────

class RPSStates(StatesGroup):
    """Rock-Paper-Scissors phase."""
    waiting_choice     = State()


class PenaltyStates(StatesGroup):
    """Active penalty round."""
    waiting_shooter    = State()
    waiting_goalkeeper = State()
