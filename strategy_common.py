from players import Player
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from draft import Draft


player_expected_score: Callable[[Player], float] = lambda player: -player.expected_gamely_score

POSITION_NUM_MAPPING: dict[str, int] = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "AR": 1, "SK": 1, "BENCH": 7}
FLEX_POSITIONS: tuple[str, str, str] = ("WR", "RB", "TE")

class DraftStrategy:
    def __init__(self, name: str, strategy: Callable[["Draft"], Player]):
        self.name: str = name
        self.strategy: Callable[["Draft"], Player] = strategy


class DraftedTeam:
    def __init__(self, drafter_name: str, strategy: DraftStrategy):
        self.drafter_name: str = drafter_name
        self.players: list[Player] = []
        self.strategy: DraftStrategy = strategy


    def expected_gamely_score(self) -> float:
        expected_score = 0
        for position, num in POSITION_NUM_MAPPING.items():
            if position in ("AR", "SK"):
                continue
            starting_position_players: list[Player] = self.get_players_at_position(position)[:num]

            for starter in starting_position_players:
                expected_score += starter.expected_gamely_score

        return expected_score
    
    
    def get_players_at_position(self, position: str) -> list[Player]:
        players: list = []

        flex_starters: list[Player] = []
        if position == "FLEX":
            flex_starters = self.get_players_at_position("RB")[:2] +\
                    self.get_players_at_position("WR")[:2] + self.get_players_at_position("TE")[:1]

        for player in self.players:
            if player.position == position:
                players.append(player)

            elif position == "FLEX" and player.position in FLEX_POSITIONS and player not in flex_starters:
                players.append(player)

        return sorted(players, key=player_expected_score)
    
        
    def get_non_full_positions(self) -> set[str]:
        non_full_positions: set[str] = set()

        for position, number in POSITION_NUM_MAPPING.items():
            if len(self.get_players_at_position(position)) < number:
                non_full_positions.add(position)

        if "FLEX" in non_full_positions:
            non_full_positions.remove("FLEX")
            non_full_positions.update(FLEX_POSITIONS)

        return set(non_full_positions) - {"BENCH"}