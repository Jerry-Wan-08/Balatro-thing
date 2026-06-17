"""
=============================================================================
PokerRogue - A Balatro-Inspired Poker Roguelite
=============================================================================
Author      : Claude (Anthropic) — generated for educational coursework
Version     : 1.0
Engine      : Python 3.8+ / Pygame 2.x

Description:
    PokerRogue is a roguelite card game inspired by Balatro. Players are dealt
    a hand of playing cards and must select cards to form the best poker hand
    possible, scoring enough chips to beat escalating blind targets.  Between
    rounds they can visit a shop to buy Joker cards that grant powerful passive
    bonuses.  The game ends when the player fails to beat a blind.

Controls:
    Mouse       – click cards to select / deselect them
    PLAY Button – score the selected hand (up to 5 cards)
    DISCARD     – discard selected cards and draw replacements (limited)
    SHOP        – visit the shop between rounds (when available)

Poker Hand Rankings (lowest → highest):
    High Card → Pair → Two Pair → Three of a Kind → Straight →
    Flush → Full House → Four of a Kind → Straight Flush → Royal Flush

How Scoring Works:
    Every hand has a base Chips value and a Multiplier (Mult).
    Score = Chips × Mult.  Jokers in your collection modify these values.
    Beat the Blind target to advance to the next round.

Jokers (examples):
    • Greedy Joker  – +4 Mult when any Diamond is scored
    • Lusty Joker   – +4 Mult when any Heart is scored
    • Wrathful Joker– +4 Mult when any Spade is scored
    • Gluttonous J. – +4 Mult when any Club is scored
    • Jolly Joker   – +8 Mult if hand contains a Pair
    • Zany Joker    – +12 Mult if hand contains a Three of a Kind
    • Mad Joker     – +10 Mult if hand contains a Two Pair
    • Crazy Joker   – +12 Mult if hand contains a Straight
    • Droll Joker   – +10 Mult if hand contains a Flush

Sources / References:
    • Balatro (LocalThunk, 2024) — original game this is inspired by
    • Pygame documentation: https://www.pygame.org/docs/
    • Poker hand evaluation logic adapted from standard combinatorics rules
    • Colour palette inspired by Balatro's deep-green felt aesthetic
    • Font rendering uses Pygame's built-in freetype module
=============================================================================
"""

import pygame
import random
import sys
import math
from enum import Enum, auto
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS & CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

SCREEN_WIDTH  = 1280
SCREEN_HEIGHT = 720
FPS           = 60
GAME_TITLE    = "PokerRogue"

# Card dimensions
CARD_W = 80
CARD_H = 110
CARD_RADIUS = 8          # rounded corner radius

# Colours — dark poker-table aesthetic
COL_BG          = (18, 42, 28)       # deep green felt
COL_BG2         = (13, 30, 20)       # darker panel
COL_GOLD        = (255, 210, 60)     # highlights / score
COL_WHITE       = (245, 240, 230)    # card face
COL_CARD_BACK   = (30, 60, 100)      # card back pattern
COL_RED         = (210, 50, 50)      # Hearts / Diamonds
COL_BLACK_SUIT  = (20, 20, 20)       # Spades / Clubs
COL_SELECTED    = (255, 230, 80)     # selection glow
COL_BTN_PLAY    = (60, 180, 80)      # play button
COL_BTN_DISC    = (180, 80, 50)      # discard button
COL_BTN_HOVER   = (200, 200, 200)    # button hover overlay
COL_PANEL       = (25, 55, 38)       # side-panel background
COL_JOKER_BG    = (80, 40, 100)      # joker card background
COL_BLIND_BAR   = (80, 160, 100)     # progress bar fill
COL_TEXT_DIM    = (140, 180, 150)    # dimmed text
COL_SHOP_BG     = (20, 20, 40)
COL_HELP_BG     = (10, 10, 25)

# Layout positions
HAND_Y          = 540               # y-centre of player hand
SCORE_AREA_Y    = 60                # y of score / blind display
JOKER_AREA_Y    = 20                # joker strip y
JOKER_W         = 70
JOKER_H         = 95

# Game limits
MAX_HAND_SIZE   = 8
MAX_JOKERS      = 5
MAX_DISCARDS    = 3                 # discards per round
ROUNDS_PER_ANTE = 3                 # Small / Big / Boss
SHOP_JOKER_SLOTS= 3                 # jokers offered in shop each visit

# Hand base scoring table   (chips, multiplier)
HAND_SCORES = {
    "High Card"       : (5,  1),
    "Pair"            : (10, 2),
    "Two Pair"        : (20, 2),
    "Three of a Kind" : (30, 3),
    "Straight"        : (30, 4),
    "Flush"           : (35, 4),
    "Full House"      : (40, 4),
    "Four of a Kind"  : (60, 7),
    "Straight Flush"  : (100, 8),
    "Royal Flush"     : (100, 8),
}


# ──────────────────────────────────────────────────────────────────────────────
# ENUMERATIONS
# ──────────────────────────────────────────────────────────────────────────────

class GameState(Enum):
    """Top-level game-state machine values."""
    PLAYING   = auto()
    SCORING   = auto()
    SHOP      = auto()
    GAME_OVER = auto()
    HELP      = auto()
    MAIN_MENU = auto()


class Suit(Enum):
    """The four playing-card suits."""
    HEARTS   = "♥"
    DIAMONDS = "♦"
    CLUBS    = "♣"
    SPADES   = "♠"


# ──────────────────────────────────────────────────────────────────────────────
# CLASS: Card
# ──────────────────────────────────────────────────────────────────────────────

class Card:
    """
    Represents a single playing card.

    Attributes:
        rank  (int)  : numeric rank 1 (Ace) – 13 (King)
        suit  (Suit) : the card's suit enum
        _selected (bool) : private flag — is card selected by player?
        rect (pygame.Rect) : screen position for click detection
        anim_y (float)     : y-offset used for selection animation
    """

    RANK_NAMES = {1: "A", 11: "J", 12: "Q", 13: "K"}

    def __init__(self, rank: int, suit: Suit):
        self.rank = rank
        self.suit = suit
        self._selected = False      # private — toggled via select()
        self.rect      = pygame.Rect(0, 0, CARD_W, CARD_H)
        self.anim_y    = 0.0        # vertical animation offset (pixels)
        self._target_y = 0.0

    # ------------------------------------------------------------------
    # Private helper
    # ------------------------------------------------------------------
    def _get_display_rank(self) -> str:
        """Return the human-readable rank string (private helper)."""
        return self.RANK_NAMES.get(self.rank, str(self.rank))

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def select(self) -> None:
        """Toggle the card's selection state and set animation target."""
        self._selected = not self._selected
        self._target_y = -22.0 if self._selected else 0.0

    @property
    def is_selected(self) -> bool:
        """Read-only property exposing the private _selected flag."""
        return self._selected

    @property
    def suit_colour(self) -> tuple:
        """Return the correct colour for this card's suit symbol."""
        if self.suit in (Suit.HEARTS, Suit.DIAMONDS):
            return COL_RED
        return COL_BLACK_SUIT

    def update(self, dt: float) -> None:
        """Smoothly animate card lift/drop each frame."""
        diff = self._target_y - self.anim_y
        self.anim_y += diff * min(dt * 18.0, 1.0)   # lerp towards target

    def draw(self, surface: pygame.Surface, font_sm, font_lg) -> None:
        """
        Render the card onto *surface* at its rect position,
        offset by the current animation value.
        """
        draw_rect = pygame.Rect(
            self.rect.x,
            self.rect.y + int(self.anim_y),
            CARD_W, CARD_H
        )

        # Selection glow — drawn behind card
        if self._selected:
            glow = draw_rect.inflate(8, 8)
            pygame.draw.rect(surface, COL_SELECTED, glow, border_radius=CARD_RADIUS + 3)

        # Card face background
        pygame.draw.rect(surface, COL_WHITE, draw_rect, border_radius=CARD_RADIUS)
        pygame.draw.rect(surface, (180, 175, 165), draw_rect, 1, border_radius=CARD_RADIUS)

        rank_str = self._get_display_rank()
        colour   = self.suit_colour
        suit_str = self.suit.value

        # Top-left rank + suit
        rank_surf = font_sm.render(rank_str, True, colour)
        suit_surf = font_sm.render(suit_str, True, colour)
        surface.blit(rank_surf, (draw_rect.x + 5, draw_rect.y + 4))
        surface.blit(suit_surf, (draw_rect.x + 5, draw_rect.y + 4 + rank_surf.get_height()))

        # Centre suit symbol
        big_suit = font_lg.render(suit_str, True, colour)
        bx = draw_rect.centerx - big_suit.get_width() // 2
        by = draw_rect.centery - big_suit.get_height() // 2
        surface.blit(big_suit, (bx, by))

        # Bottom-right rank + suit (rotated 180° effect via mirrored coords)
        surface.blit(rank_surf, (
            draw_rect.right - rank_surf.get_width() - 5,
            draw_rect.bottom - rank_surf.get_height() - suit_surf.get_height() - 4
        ))
        surface.blit(suit_surf, (
            draw_rect.right - suit_surf.get_width() - 5,
            draw_rect.bottom - suit_surf.get_height() - 4
        ))

    def __repr__(self) -> str:
        return f"Card({self._get_display_rank()}{self.suit.value})"


# ──────────────────────────────────────────────────────────────────────────────
# CLASS: Deck
# ──────────────────────────────────────────────────────────────────────────────

class Deck:
    """
    Standard 52-card deck with shuffle and draw functionality.

    The deck manages its own internal list of remaining cards and
    provides a clean interface for drawing without replacement.
    """

    def __init__(self):
        self._cards: list[Card] = []
        self._build()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _build(self) -> None:
        """Construct all 52 cards and shuffle them."""
        self._cards = [
            Card(rank, suit)
            for suit in Suit
            for rank in range(1, 14)
        ]
        self._shuffle()

    def _shuffle(self) -> None:
        """Randomly shuffle the internal deck (private)."""
        random.shuffle(self._cards)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def draw(self, count: int = 1) -> list[Card]:
        """
        Draw *count* cards from the top of the deck.
        Rebuilds the deck automatically if it runs out.
        """
        drawn = []
        for _ in range(count):
            if not self._cards:
                self._build()           # reshuffle when exhausted
            drawn.append(self._cards.pop())
        return drawn

    @property
    def remaining(self) -> int:
        """Number of cards left in the deck."""
        return len(self._cards)

    def reset(self) -> None:
        """Fully reset and reshuffle the deck for a new round."""
        self._build()


# ──────────────────────────────────────────────────────────────────────────────
# CLASS: Joker
# ──────────────────────────────────────────────────────────────────────────────

class Joker:
    """
    A Joker card that grants a passive bonus when scoring hands.

    Each Joker has a trigger condition checked against the played hand
    and scoring cards.  When triggered it adds to chips and/or mult.
    """

    def __init__(self, name: str, description: str,
                 chips_bonus: int, mult_bonus: int,
                 trigger_suit: Optional[Suit] = None,
                 trigger_hand: Optional[str]  = None,
                 cost: int = 4):
        self.name         = name
        self.description  = description
        self.chips_bonus  = chips_bonus
        self.mult_bonus   = mult_bonus
        self.trigger_suit = trigger_suit   # activates when this suit is in play
        self.trigger_hand = trigger_hand   # activates for this hand type
        self.cost         = cost

    def _is_triggered(self, hand_name: str, scored_cards: list[Card]) -> bool:
        """
        Private trigger check — returns True if this Joker activates
        for the given hand and list of scored cards.
        """
        if self.trigger_hand and self.trigger_hand in hand_name:
            return True
        if self.trigger_suit:
            for card in scored_cards:
                if card.suit == self.trigger_suit:
                    return True
        return False

    def apply(self, chips: int, mult: int,
              hand_name: str, scored_cards: list[Card]) -> tuple[int, int]:
        """
        Apply this Joker's bonuses if triggered.
        Returns updated (chips, mult) tuple.
        """
        if self._is_triggered(hand_name, scored_cards):
            chips += self.chips_bonus
            mult  += self.mult_bonus
        return chips, mult

    def draw(self, surface: pygame.Surface, x: int, y: int,
             font_sm, font_xs) -> None:
        """Render the Joker card in the Joker tray."""
        rect = pygame.Rect(x, y, JOKER_W, JOKER_H)
        pygame.draw.rect(surface, COL_JOKER_BG, rect, border_radius=6)
        pygame.draw.rect(surface, COL_GOLD, rect, 2, border_radius=6)

        # Joker face emoji / label
        jok = font_sm.render("🃏", True, COL_GOLD)
        surface.blit(jok, (rect.centerx - jok.get_width()//2, rect.y + 6))

        # Wrap name into two lines if needed
        words  = self.name.split()
        line1  = " ".join(words[:2])
        line2  = " ".join(words[2:]) if len(words) > 2 else ""
        t1 = font_xs.render(line1, True, COL_WHITE)
        surface.blit(t1, (rect.centerx - t1.get_width()//2, rect.y + 38))
        if line2:
            t2 = font_xs.render(line2, True, COL_WHITE)
            surface.blit(t2, (rect.centerx - t2.get_width()//2, rect.y + 52))

    def __repr__(self) -> str:
        return f"Joker({self.name})"


# ──────────────────────────────────────────────────────────────────────────────
# HAND EVALUATOR — standalone functions
# ──────────────────────────────────────────────────────────────────────────────

def _rank_counts(cards: list[Card]) -> dict:
    """Return {rank: count} for a list of cards."""
    counts = {}
    for card in cards:
        counts[card.rank] = counts.get(card.rank, 0) + 1
    return counts


def _is_flush(cards: list[Card]) -> bool:
    """Return True if all cards share the same suit."""
    return len({c.suit for c in cards}) == 1


def _is_straight(cards: list[Card]) -> bool:
    """
    Return True if cards form a straight (consecutive ranks).
    Handles the special Ace-high (A=14) and Ace-low (A=1) cases.
    """
    if len(cards) < 5:
        return False
    ranks = sorted(c.rank for c in cards)
    # Ace-low: treat Ace as 1 (already stored as 1, so check 1-2-3-4-5)
    # Ace-high: treat Ace as 14
    ace_high = sorted([14 if r == 1 else r for r in ranks])
    normal   = ranks
    def consec(lst):
        return all(lst[i+1] - lst[i] == 1 for i in range(len(lst)-1))
    return consec(normal) or consec(ace_high)


def evaluate_hand(cards: list[Card]) -> tuple[str, list[Card]]:
    """
    Evaluate the best poker hand from up to 5 cards.

    Returns:
        (hand_name, scored_cards) where scored_cards are the cards
        that contribute to the hand (used for Joker triggers).
    """
    if not cards:
        return "High Card", []

    n      = len(cards)
    counts = _rank_counts(cards)
    freq   = sorted(counts.values(), reverse=True)
    flush  = _is_flush(cards) and n == 5
    straight = _is_straight(cards) and n == 5

    # Determine hand name
    if straight and flush:
        ranks = sorted(c.rank for c in cards)
        if 1 in ranks and 13 in ranks:    # A + K = royal
            hand_name = "Royal Flush"
        else:
            hand_name = "Straight Flush"
    elif freq[0] == 4:
        hand_name = "Four of a Kind"
    elif freq[0] == 3 and len(freq) > 1 and freq[1] == 2:
        hand_name = "Full House"
    elif flush:
        hand_name = "Flush"
    elif straight:
        hand_name = "Straight"
    elif freq[0] == 3:
        hand_name = "Three of a Kind"
    elif freq[0] == 2 and len(freq) > 1 and freq[1] == 2:
        hand_name = "Two Pair"
    elif freq[0] == 2:
        hand_name = "Pair"
    else:
        hand_name = "High Card"

    return hand_name, cards     # all played cards are "scoring" cards


def calculate_score(hand_name: str, scored_cards: list[Card],
                    jokers: list[Joker]) -> tuple[int, int, int]:
    """
    Calculate the final score for a played hand.

    Args:
        hand_name    : string name of the evaluated hand
        scored_cards : cards contributing to the hand
        jokers       : player's active Joker collection

    Returns:
        (chips, mult, total_score) after applying all Joker bonuses
    """
    base_chips, base_mult = HAND_SCORES.get(hand_name, (5, 1))

    # Each scored card contributes its rank value as bonus chips
    card_chips = sum(min(c.rank, 10) for c in scored_cards)
    chips = base_chips + card_chips
    mult  = base_mult

    # Apply each Joker in sequence
    for joker in jokers:
        chips, mult = joker.apply(chips, mult, hand_name, scored_cards)

    return chips, mult, chips * mult


# ──────────────────────────────────────────────────────────────────────────────
# JOKER CATALOGUE — factory function
# ──────────────────────────────────────────────────────────────────────────────

def _all_jokers() -> list[Joker]:
    """Return the full catalogue of available Joker cards."""
    return [
        Joker("Greedy Joker",    "+4 Mult per ♦ scored",   0,  4, trigger_suit=Suit.DIAMONDS, cost=4),
        Joker("Lusty Joker",     "+4 Mult per ♥ scored",   0,  4, trigger_suit=Suit.HEARTS,   cost=4),
        Joker("Wrathful Joker",  "+4 Mult per ♠ scored",   0,  4, trigger_suit=Suit.SPADES,   cost=4),
        Joker("Gluttonous Joker","+4 Mult per ♣ scored",   0,  4, trigger_suit=Suit.CLUBS,    cost=4),
        Joker("Jolly Joker",     "+8 Mult if Pair",         0,  8, trigger_hand="Pair",        cost=5),
        Joker("Zany Joker",      "+12 Mult if Three",       0, 12, trigger_hand="Three",       cost=6),
        Joker("Mad Joker",       "+10 Mult if Two Pair",    0, 10, trigger_hand="Two Pair",    cost=5),
        Joker("Crazy Joker",     "+12 Mult if Straight",    0, 12, trigger_hand="Straight",    cost=7),
        Joker("Droll Joker",     "+10 Mult if Flush",       0, 10, trigger_hand="Flush",       cost=7),
        Joker("Sly Joker",       "+50 chips if Pair",      50,  0, trigger_hand="Pair",        cost=3),
        Joker("Wily Joker",      "+100 chips if Three",   100,  0, trigger_hand="Three",       cost=5),
        Joker("Clever Joker",    "+80 chips if Two Pair",  80,  0, trigger_hand="Two Pair",    cost=4),
        Joker("Devious Joker",   "+100 chips Straight",   100,  0, trigger_hand="Straight",    cost=6),
        Joker("Crafty Joker",    "+80 chips if Flush",     80,  0, trigger_hand="Flush",       cost=6),
        Joker("Half Joker",      "+20 Mult ≤3 cards",       0, 20, cost=5),    # special: handled inline
        Joker("Joker",           "+4 Mult always",          0,  4, cost=2),    # no trigger = always fires
    ]


# ──────────────────────────────────────────────────────────────────────────────
# CLASS: Button — simple UI widget
# ──────────────────────────────────────────────────────────────────────────────

class Button:
    """A clickable rectangle button with hover effect."""

    def __init__(self, rect: pygame.Rect, label: str,
                 colour: tuple, text_colour: tuple = COL_WHITE):
        self.rect        = rect
        self.label       = label
        self.colour      = colour
        self.text_colour = text_colour
        self._hovered    = False

    def update(self, mouse_pos: tuple) -> None:
        """Update hover state based on mouse position."""
        self._hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, event: pygame.event.Event) -> bool:
        """Return True if a MOUSEBUTTONDOWN event hit this button."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False

    def draw(self, surface: pygame.Surface, font) -> None:
        """Render the button to *surface*."""
        col = tuple(min(c + 30, 255) for c in self.colour) if self._hovered else self.colour
        pygame.draw.rect(surface, col, self.rect, border_radius=6)
        pygame.draw.rect(surface, COL_WHITE, self.rect, 2, border_radius=6)
        text = font.render(self.label, True, self.text_colour)
        surface.blit(text, (
            self.rect.centerx - text.get_width()  // 2,
            self.rect.centery - text.get_height() // 2
        ))


# ──────────────────────────────────────────────────────────────────────────────
# CLASS: ScorePopup — floating score animation
# ──────────────────────────────────────────────────────────────────────────────

class ScorePopup:
    """A temporary floating text that rises and fades after scoring."""

    def __init__(self, text: str, x: int, y: int, colour: tuple = COL_GOLD):
        self.text      = text
        self.x         = float(x)
        self.y         = float(y)
        self.colour    = colour
        self.lifetime  = 2.0      # seconds to live
        self.elapsed   = 0.0
        self.alive     = True

    def update(self, dt: float) -> None:
        self.elapsed += dt
        self.y       -= dt * 40   # drift upward
        if self.elapsed >= self.lifetime:
            self.alive = False

    def draw(self, surface: pygame.Surface, font) -> None:
        alpha = max(0, int(255 * (1.0 - self.elapsed / self.lifetime)))
        surf  = font.render(self.text, True, self.colour)
        surf.set_alpha(alpha)
        surface.blit(surf, (int(self.x) - surf.get_width()//2, int(self.y)))


# ──────────────────────────────────────────────────────────────────────────────
# CLASS: Game — main controller
# ──────────────────────────────────────────────────────────────────────────────

class Game:
    """
    Top-level game controller.

    Owns all game state, orchestrates the state machine, and
    delegates rendering / input handling to sub-methods.
    """

    # ── Blind schedule: list of (name, target_score) per ante
    BLIND_SCHEDULE = [
        [("Small Blind", 300),  ("Big Blind", 450),  ("Boss Blind", 600)],
        [("Small Blind", 800),  ("Big Blind", 1200), ("Boss Blind", 1600)],
        [("Small Blind", 2000), ("Big Blind", 3000), ("Boss Blind", 4000)],
        [("Small Blind", 5000), ("Big Blind", 7500), ("Boss Blind", 10000)],
        [("Small Blind", 12000),("Big Blind", 18000),("Boss Blind", 25000)],
    ]

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self._init_fonts()
        self._reset_game()
        self.state  = GameState.MAIN_MENU

    # ------------------------------------------------------------------
    # Private initialisation helpers
    # ------------------------------------------------------------------

    def _init_fonts(self) -> None:
        """Load all required fonts (private)."""
        pygame.font.init()
        self.font_xl  = pygame.font.SysFont("Arial",  36, bold=True)
        self.font_lg  = pygame.font.SysFont("Arial",  28, bold=True)
        self.font_md  = pygame.font.SysFont("Arial",  20, bold=True)
        self.font_sm  = pygame.font.SysFont("Arial",  16)
        self.font_xs  = pygame.font.SysFont("Arial",  13)

    def _reset_game(self) -> None:
        """Fully reset all game variables for a new game (private)."""
        self.deck          = Deck()
        self.hand: list[Card] = []
        self.jokers: list[Joker] = []
        self.score         = 0          # cumulative run score (display only)
        self.round_score   = 0          # chips scored this round so far
        self.ante          = 0          # current ante index (row in schedule)
        self.blind_idx     = 0          # 0/1/2 within the ante
        self.hands_left    = 4          # play attempts per round
        self.discards_left = MAX_DISCARDS
        self.gold          = 4          # starting gold for shop
        self.popups: list[ScorePopup] = []
        self.last_hand_name = ""
        self.last_chips     = 0
        self.last_mult      = 0
        self.last_total     = 0
        self.shop_jokers: list[Joker] = []
        self._deal_hand()
        self._build_buttons()

    def _deal_hand(self) -> None:
        """Deal cards up to MAX_HAND_SIZE (private)."""
        needed = MAX_HAND_SIZE - len(self.hand)
        if needed > 0:
            self.hand.extend(self.deck.draw(needed))
        self._layout_hand()

    def _layout_hand(self) -> None:
        """Position hand cards horizontally centred (private)."""
        n     = len(self.hand)
        total = n * CARD_W + (n - 1) * 12
        start = SCREEN_WIDTH // 2 - total // 2
        for i, card in enumerate(self.hand):
            card.rect.x = start + i * (CARD_W + 12)
            card.rect.y = HAND_Y - CARD_H // 2

    def _build_buttons(self) -> None:
        """Construct all UI buttons (private)."""
        self.btn_play    = Button(pygame.Rect(50,  620, 160, 50), "▶  PLAY HAND", COL_BTN_PLAY)
        self.btn_discard = Button(pygame.Rect(230, 620, 160, 50), "✕  DISCARD",   COL_BTN_DISC)
        self.btn_shop    = Button(pygame.Rect(SCREEN_WIDTH//2 - 80, 340, 160, 50),
                                  "🛒  ENTER SHOP", (60, 60, 160))
        self.btn_help    = Button(pygame.Rect(SCREEN_WIDTH - 110, 10,  95, 36), "? HELP",  (40, 80, 60))
        self.btn_menu    = Button(pygame.Rect(SCREEN_WIDTH - 220, 10, 100, 36), "⌂ MENU",  (60, 40, 40))

        # Shop buy buttons (populated when shop opens)
        self.shop_buy_btns: list[Button] = []

        # Main-menu buttons
        self.btn_start   = Button(pygame.Rect(SCREEN_WIDTH//2 - 100, 380, 200, 55),
                                  "NEW GAME", COL_BTN_PLAY)
        self.btn_help_mm = Button(pygame.Rect(SCREEN_WIDTH//2 - 100, 460, 200, 55),
                                  "HOW TO PLAY", (60, 60, 160))

    # ------------------------------------------------------------------
    # Properties / accessors
    # ------------------------------------------------------------------

    @property
    def _current_blind(self) -> tuple[str, int]:
        """Return (name, target) for the current blind."""
        schedule = self.BLIND_SCHEDULE
        if self.ante < len(schedule):
            blinds = schedule[self.ante]
            if self.blind_idx < len(blinds):
                return blinds[self.blind_idx]
        return ("Infinite", 999_999)

    @property
    def _selected_cards(self) -> list[Card]:
        """Return the currently selected cards in hand."""
        return [c for c in self.hand if c.is_selected]

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def _open_shop(self) -> None:
        """Transition to the shop state and populate it with Jokers."""
        all_j = _all_jokers()
        random.shuffle(all_j)
        # Exclude jokers the player already owns
        owned_names  = {j.name for j in self.jokers}
        available    = [j for j in all_j if j.name not in owned_names]
        self.shop_jokers = available[:SHOP_JOKER_SLOTS]

        # Build buy buttons
        self.shop_buy_btns = []
        for i in range(len(self.shop_jokers)):
            bx = 200 + i * 280
            by = 440
            self.shop_buy_btns.append(
                Button(pygame.Rect(bx, by, 160, 44), "Buy  $" + str(self.shop_jokers[i].cost),
                       (60, 130, 60))
            )

        self.btn_shop_leave = Button(pygame.Rect(SCREEN_WIDTH//2 - 90, 570, 180, 48),
                                     "Leave Shop ➜", (80, 50, 50))
        self.state = GameState.SHOP

    def _advance_blind(self) -> None:
        """Move to the next blind / ante after successfully beating one."""
        self.blind_idx += 1
        if self.blind_idx >= ROUNDS_PER_ANTE:
            self.blind_idx = 0
            self.ante     += 1
            if self.ante >= len(self.BLIND_SCHEDULE):
                self.ante = len(self.BLIND_SCHEDULE) - 1  # stay on last ante

        self.round_score   = 0
        self.hands_left    = 4
        self.discards_left = MAX_DISCARDS
        self.gold         += 3           # income between rounds
        self.deck.reset()
        self.hand.clear()
        self._deal_hand()
        self._open_shop()

    def _game_over(self) -> None:
        """Transition to game-over screen."""
        self.state = GameState.GAME_OVER

    # ------------------------------------------------------------------
    # Core play action
    # ------------------------------------------------------------------

    def _play_hand(self) -> None:
        """
        Score the currently selected cards, apply Joker bonuses,
        add to round score, and check win / loss conditions.
        """
        selected = self._selected_cards
        if not selected:
            return
        if len(selected) > 5:
            return       # player must select at most 5

        hand_name, scored = evaluate_hand(selected)

        # Special: Half Joker bonus — +20 Mult if ≤3 cards played
        chips, mult = HAND_SCORES.get(hand_name, (5, 1))
        card_chips  = sum(min(c.rank, 10) for c in scored)
        chips      += card_chips

        for joker in self.jokers:
            if joker.name == "Half Joker" and len(selected) <= 3:
                mult += 20
            elif joker.name == "Joker":
                mult += 4
            else:
                chips, mult = joker.apply(chips, mult, hand_name, scored)

        total = chips * mult

        # Store for display
        self.last_hand_name = hand_name
        self.last_chips     = chips
        self.last_mult      = mult
        self.last_total     = total

        self.round_score += total
        self.score       += total

        # Floating popup
        self.popups.append(ScorePopup(
            f"+{total:,}",
            SCREEN_WIDTH // 2, HAND_Y - 80,
            COL_GOLD
        ))
        self.popups.append(ScorePopup(
            f"{hand_name}!",
            SCREEN_WIDTH // 2, HAND_Y - 110,
            (200, 230, 255)
        ))

        # Remove scored cards and redraw
        for card in selected:
            self.hand.remove(card)
        self._deal_hand()
        self.hands_left -= 1

        # Check win condition
        blind_name, target = self._current_blind
        if self.round_score >= target:
            self._advance_blind()
            return

        # Check loss condition
        if self.hands_left <= 0:
            self._game_over()

    def _discard_selected(self) -> None:
        """Discard selected cards and draw replacements."""
        if self.discards_left <= 0:
            return
        selected = self._selected_cards
        if not selected:
            return

        for card in selected:
            self.hand.remove(card)
        self.discards_left -= 1
        self._deal_hand()

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------

    def update(self, dt: float, events: list) -> None:
        """Process events and update all game objects each frame."""
        mouse_pos = pygame.mouse.get_pos()

        # Update button hover states
        if self.state == GameState.PLAYING:
            self.btn_play.update(mouse_pos)
            self.btn_discard.update(mouse_pos)
            self.btn_help.update(mouse_pos)
            self.btn_menu.update(mouse_pos)
            for card in self.hand:
                card.update(dt)

        # Update floating popups
        for popup in self.popups:
            popup.update(dt)
        self.popups = [p for p in self.popups if p.alive]

        # Handle events
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if self.state == GameState.MAIN_MENU:
                self._handle_main_menu(event)
            elif self.state == GameState.PLAYING:
                self._handle_playing(event)
            elif self.state == GameState.SHOP:
                self._handle_shop(event)
            elif self.state == GameState.GAME_OVER:
                self._handle_game_over(event)
            elif self.state == GameState.HELP:
                self._handle_help(event)

    # ------------------------------------------------------------------
    # Event handlers per state
    # ------------------------------------------------------------------

    def _handle_main_menu(self, event: pygame.event.Event) -> None:
        mouse_pos = pygame.mouse.get_pos()
        self.btn_start.update(mouse_pos)
        self.btn_help_mm.update(mouse_pos)

        if self.btn_start.is_clicked(event):
            self._reset_game()
            self.state = GameState.PLAYING
        elif self.btn_help_mm.is_clicked(event):
            self.state = GameState.HELP

    def _handle_playing(self, event: pygame.event.Event) -> None:
        if self.btn_play.is_clicked(event):
            self._play_hand()
        elif self.btn_discard.is_clicked(event):
            self._discard_selected()
        elif self.btn_help.is_clicked(event):
            self.state = GameState.HELP
        elif self.btn_menu.is_clicked(event):
            self.state = GameState.MAIN_MENU
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Card click — toggle selection
            for card in self.hand:
                anim_rect = pygame.Rect(card.rect.x,
                                        card.rect.y + int(card.anim_y),
                                        CARD_W, CARD_H)
                if anim_rect.collidepoint(event.pos):
                    # Enforce max 5 selected
                    sel = self._selected_cards
                    if card.is_selected or len(sel) < 5:
                        card.select()
                    break

    def _handle_shop(self, event: pygame.event.Event) -> None:
        mouse_pos = pygame.mouse.get_pos()
        self.btn_shop_leave.update(mouse_pos)
        for btn in self.shop_buy_btns:
            btn.update(mouse_pos)

        if self.btn_shop_leave.is_clicked(event):
            self.state = GameState.PLAYING
            return

        for i, btn in enumerate(self.shop_buy_btns):
            if btn.is_clicked(event) and i < len(self.shop_jokers):
                joker = self.shop_jokers[i]
                if (self.gold >= joker.cost and
                        len(self.jokers) < MAX_JOKERS):
                    self.gold -= joker.cost
                    self.jokers.append(joker)
                    self.shop_jokers.pop(i)
                    self.shop_buy_btns.pop(i)
                    break

    def _handle_game_over(self, event: pygame.event.Event) -> None:
        mouse_pos = pygame.mouse.get_pos()
        self.btn_start.update(mouse_pos)
        if self.btn_start.is_clicked(event):
            self._reset_game()
            self.state = GameState.PLAYING

    def _handle_help(self, event: pygame.event.Event) -> None:
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
            self.state = GameState.PLAYING if self.state != GameState.MAIN_MENU else GameState.MAIN_MENU

    # ------------------------------------------------------------------
    # Draw dispatcher
    # ------------------------------------------------------------------

    def draw(self) -> None:
        """Render the correct screen for the current game state."""
        self.screen.fill(COL_BG)
        if self.state == GameState.MAIN_MENU:
            self._draw_main_menu()
        elif self.state == GameState.PLAYING:
            self._draw_playing()
        elif self.state == GameState.SHOP:
            self._draw_shop()
        elif self.state == GameState.GAME_OVER:
            self._draw_game_over()
        elif self.state == GameState.HELP:
            self._draw_help()

    # ------------------------------------------------------------------
    # Draw: main menu
    # ------------------------------------------------------------------

    def _draw_main_menu(self) -> None:
        """Render the main menu screen."""
        # Animated card background
        t = pygame.time.get_ticks() / 1000.0
        for i in range(8):
            x = (i * 180 + int(t * 20) % SCREEN_WIDTH) % SCREEN_WIDTH
            y = 100 + int(math.sin(t * 0.5 + i) * 40)
            c = Card(random.randint(1, 13), list(Suit)[i % 4])
            c.rect.x = x
            c.rect.y = y
            # draw a simplified card back
            r = pygame.Rect(x, y, CARD_W, CARD_H)
            pygame.draw.rect(self.screen, COL_CARD_BACK, r, border_radius=CARD_RADIUS)
            pygame.draw.rect(self.screen, COL_GOLD, r, 2, border_radius=CARD_RADIUS)

        # Title
        title = self.font_xl.render("♠  PokerRogue  ♠", True, COL_GOLD)
        sub   = self.font_md.render("A Balatro-Inspired Roguelite", True, COL_TEXT_DIM)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 260))
        self.screen.blit(sub,   (SCREEN_WIDTH//2 - sub.get_width()//2,   314))

        self.btn_start.draw(self.screen, self.font_md)
        self.btn_help_mm.draw(self.screen, self.font_md)

        credit = self.font_xs.render("Use mouse to select cards • Play the best poker hand • Beat the blind!", True, COL_TEXT_DIM)
        self.screen.blit(credit, (SCREEN_WIDTH//2 - credit.get_width()//2, 560))

    # ------------------------------------------------------------------
    # Draw: playing
    # ------------------------------------------------------------------

    def _draw_playing(self) -> None:
        """Render the main gameplay screen."""
        self._draw_top_bar()
        self._draw_joker_tray()
        self._draw_hand_area()
        self._draw_score_info()
        self._draw_bottom_buttons()

        # Popups (drawn last so they appear on top)
        for popup in self.popups:
            popup.draw(self.screen, self.font_lg)

    def _draw_top_bar(self) -> None:
        """Draw the blind name, target, and progress bar."""
        blind_name, target = self._current_blind
        progress = min(self.round_score / target, 1.0) if target else 1.0

        # Panel background
        pygame.draw.rect(self.screen, COL_BG2, (0, 0, SCREEN_WIDTH, 54))

        # Blind label
        b_label = self.font_md.render(
            f"Ante {self.ante + 1} — {blind_name}", True, COL_GOLD)
        self.screen.blit(b_label, (14, 14))

        # Progress bar
        bar_x, bar_y, bar_w, bar_h = 280, 16, 400, 22
        pygame.draw.rect(self.screen, (40, 60, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        pygame.draw.rect(self.screen, COL_BLIND_BAR,
                         (bar_x, bar_y, int(bar_w * progress), bar_h), border_radius=4)
        pygame.draw.rect(self.screen, COL_WHITE, (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)

        score_txt = self.font_sm.render(
            f"{self.round_score:,} / {target:,}", True, COL_WHITE)
        self.screen.blit(score_txt, (bar_x + bar_w + 10, bar_y + 2))

        # Hands / Discards / Gold
        info = (f"Hands: {self.hands_left}   "
                f"Discards: {self.discards_left}   "
                f"Gold: ${self.gold}")
        info_surf = self.font_sm.render(info, True, COL_TEXT_DIM)
        self.screen.blit(info_surf, (SCREEN_WIDTH - info_surf.get_width() - 14, 16))

        # Help / Menu buttons
        self.btn_help.draw(self.screen, self.font_xs)
        self.btn_menu.draw(self.screen, self.font_xs)

    def _draw_joker_tray(self) -> None:
        """Render the player's active Joker cards across the top."""
        label = self.font_xs.render("JOKERS:", True, COL_TEXT_DIM)
        self.screen.blit(label, (14, 62))
        for i, joker in enumerate(self.jokers):
            joker.draw(self.screen, 14 + i * (JOKER_W + 8), 78,
                       self.font_sm, self.font_xs)

        if not self.jokers:
            empty = self.font_xs.render("(none yet — visit the shop!)", True, COL_TEXT_DIM)
            self.screen.blit(empty, (80, 100))

    def _draw_hand_area(self) -> None:
        """Draw the player's hand cards."""
        # Divider line
        pygame.draw.line(self.screen, (40, 70, 50),
                         (0, HAND_Y - CARD_H // 2 - 16),
                         (SCREEN_WIDTH, HAND_Y - CARD_H // 2 - 16), 1)

        hand_label = self.font_sm.render(
            f"YOUR HAND  ({len(self._selected_cards)}/5 selected)", True, COL_TEXT_DIM)
        self.screen.blit(hand_label, (14, HAND_Y - CARD_H // 2 - 14))

        for card in self.hand:
            card.draw(self.screen, self.font_sm, self.font_lg)

    def _draw_score_info(self) -> None:
        """Show last scored hand details in the centre panel."""
        if self.last_hand_name:
            y = 195
            hn = self.font_md.render(self.last_hand_name, True, COL_GOLD)
            self.screen.blit(hn, (SCREEN_WIDTH // 2 - hn.get_width() // 2, y))
            detail = self.font_sm.render(
                f"Chips {self.last_chips}  ×  Mult {self.last_mult}"
                f"  =  {self.last_total:,}",
                True, COL_WHITE)
            self.screen.blit(detail, (SCREEN_WIDTH // 2 - detail.get_width() // 2, y + 30))

    def _draw_bottom_buttons(self) -> None:
        """Render Play and Discard buttons with contextual labels."""
        # Update button labels dynamically
        self.btn_play.label    = "▶  PLAY HAND"
        self.btn_discard.label = f"✕  DISCARD  ({self.discards_left})"
        self.btn_play.draw(self.screen,    self.font_md)
        self.btn_discard.draw(self.screen, self.font_md)

        # Selection hint
        sel = len(self._selected_cards)
        hint_col = COL_WHITE if sel > 0 else COL_TEXT_DIM
        hint = self.font_sm.render(
            f"{sel} card{'s' if sel != 1 else ''} selected — click cards to select / deselect",
            True, hint_col)
        self.screen.blit(hint, (420, 634))

    # ------------------------------------------------------------------
    # Draw: shop
    # ------------------------------------------------------------------

    def _draw_shop(self) -> None:
        """Render the between-round shop."""
        self.screen.fill(COL_SHOP_BG)

        title = self.font_xl.render("🛒  SHOP", True, COL_GOLD)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 60))

        gold_txt = self.font_lg.render(f"Gold: ${self.gold}", True, COL_GOLD)
        self.screen.blit(gold_txt, (SCREEN_WIDTH//2 - gold_txt.get_width()//2, 110))

        cap_txt = self.font_sm.render(
            f"Joker slots: {len(self.jokers)}/{MAX_JOKERS}", True, COL_TEXT_DIM)
        self.screen.blit(cap_txt, (SCREEN_WIDTH//2 - cap_txt.get_width()//2, 148))

        # Draw offered jokers
        for i, joker in enumerate(self.shop_jokers):
            bx = 200 + i * 280
            by = 200
            jrect = pygame.Rect(bx, by, 200, 210)
            pygame.draw.rect(self.screen, COL_JOKER_BG, jrect, border_radius=10)
            pygame.draw.rect(self.screen, COL_GOLD,     jrect, 2, border_radius=10)

            joker.draw(self.screen, bx + 65, by + 10, self.font_sm, self.font_xs)

            # Description (word-wrap rudimentary)
            desc = self.font_xs.render(joker.description, True, COL_WHITE)
            self.screen.blit(desc, (bx + 100 - desc.get_width()//2, by + 130))

            cost_c = self.font_sm.render(f"Cost: ${joker.cost}", True, COL_GOLD)
            self.screen.blit(cost_c, (bx + 100 - cost_c.get_width()//2, by + 155))

            if i < len(self.shop_buy_btns):
                can_buy = self.gold >= joker.cost and len(self.jokers) < MAX_JOKERS
                self.shop_buy_btns[i].colour = COL_BTN_PLAY if can_buy else (80, 80, 80)
                self.shop_buy_btns[i].draw(self.screen, self.font_sm)

        if not self.shop_jokers:
            empty = self.font_md.render("Nothing left for sale!", True, COL_TEXT_DIM)
            self.screen.blit(empty, (SCREEN_WIDTH//2 - empty.get_width()//2, 320))

        self.btn_shop_leave.draw(self.screen, self.font_md)

        hint = self.font_xs.render(
            "Jokers give powerful bonuses when you play matching hands", True, COL_TEXT_DIM)
        self.screen.blit(hint, (SCREEN_WIDTH//2 - hint.get_width()//2, 640))

    # ------------------------------------------------------------------
    # Draw: game over
    # ------------------------------------------------------------------

    def _draw_game_over(self) -> None:
        """Render the game-over screen with final stats."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        title = self.font_xl.render("GAME  OVER", True, (220, 60, 60))
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 200))

        blind_name, target = self._current_blind
        info_lines = [
            f"Failed to beat: {blind_name}",
            f"Target: {target:,} chips",
            f"You scored: {self.round_score:,} chips",
            f"Total run score: {self.score:,}",
            f"Ante reached: {self.ante + 1}",
            f"Jokers collected: {len(self.jokers)}",
        ]
        for i, line in enumerate(info_lines):
            surf = self.font_md.render(line, True, COL_WHITE)
            self.screen.blit(surf, (SCREEN_WIDTH//2 - surf.get_width()//2, 280 + i * 34))

        self.btn_start.label = "PLAY AGAIN"
        self.btn_start.rect.topleft = (SCREEN_WIDTH//2 - 100, 510)
        self.btn_start.draw(self.screen, self.font_md)

    # ------------------------------------------------------------------
    # Draw: help / instructions
    # ------------------------------------------------------------------

    def _draw_help(self) -> None:
        """Render the comprehensive help / instructions screen."""
        self.screen.fill(COL_HELP_BG)

        title = self.font_xl.render("HOW TO PLAY  —  PokerRogue", True, COL_GOLD)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 20))

        # Two-column layout
        left_lines = [
            ("OBJECTIVE", True),
            ("Beat the Blind target each round by playing", False),
            ("poker hands to score chips.", False),
            ("", False),
            ("CONTROLS", True),
            ("Click cards to select / deselect them.", False),
            ("Select up to 5 cards, then click PLAY HAND.", False),
            ("DISCARD replaces selected cards (limited).", False),
            ("", False),
            ("SCORING", True),
            ("Score = Chips × Multiplier", False),
            ("Higher hand = more base chips & multiplier.", False),
            ("Each card's rank adds bonus chips.", False),
            ("", False),
            ("JOKERS", True),
            ("Buy Jokers in the shop between rounds.", False),
            ("They add Chips or Mult when triggered.", False),
            ("You can hold up to 5 Jokers.", False),
        ]
        right_lines = [
            ("HAND RANKINGS", True),
            ("High Card     5  ×  1", False),
            ("Pair          10 ×  2", False),
            ("Two Pair      20 ×  2", False),
            ("Three of Kind 30 ×  3", False),
            ("Straight      30 ×  4", False),
            ("Flush         35 ×  4", False),
            ("Full House    40 ×  4", False),
            ("Four of Kind  60 ×  7", False),
            ("Straight Flush 100× 8", False),
            ("Royal Flush   100 × 8", False),
            ("", False),
            ("TIPS", True),
            ("Save discards for emergencies.", False),
            ("Jokers that match your hand type", False),
            ("give the best score boosts.", False),
            ("Gold income increases each round.", False),
        ]

        for i, (line, is_header) in enumerate(left_lines):
            col  = COL_GOLD if is_header else COL_WHITE
            font = self.font_sm if is_header else self.font_xs
            surf = font.render(line, True, col)
            self.screen.blit(surf, (80, 80 + i * 22))

        for i, (line, is_header) in enumerate(right_lines):
            col  = COL_GOLD if is_header else COL_WHITE
            font = self.font_sm if is_header else self.font_xs
            surf = font.render(line, True, col)
            self.screen.blit(surf, (660, 80 + i * 22))

        close = self.font_md.render("Click or press any key to close", True, COL_TEXT_DIM)
        self.screen.blit(close, (SCREEN_WIDTH//2 - close.get_width()//2, 670))


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """
    Initialise Pygame, create the window, and run the main game loop.
    This is the only function called at module level.
    """
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(GAME_TITLE)
    clock  = pygame.time.Clock()

    game = Game(screen)

    # ── Main loop
    while True:
        dt     = clock.tick(FPS) / 1000.0       # delta-time in seconds
        events = pygame.event.get()

        game.update(dt, events)
        game.draw()
        pygame.display.flip()


if __name__ == "__main__":
    main()