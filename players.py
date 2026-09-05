import csv
from pathlib import Path

PROJECTIONS_DIRECTORY_NAME: str = "projections"
PROJECTION_FILE_TEMPLATE: str = "FantasyPros_Fantasy_Football_Projections_{}.csv"

# maps the position each projection file covers to the position code used throughout the draft
POSITION_BY_PROJECTION_FILE: dict[str, str] = {"QB": "QB", "RB": "RB", "WR": "WR",
                                                "TE": "TE", "K": "SK", "DST": "AR"}

GAMES_PER_SEASON: int = 17

class Player:
    def __init__(self, name: str, position: str, expected_gamely_score: float):
        self.name: str = name
        self.position: str = position
        self.expected_gamely_score: float = expected_gamely_score

    def __str__(self) -> str:
        return f"{self.position} {self.name} with expected score {self.expected_gamely_score:.4}"
    

def read_projection_file(projection_file_position: str) -> list[Player]:
    position: str = POSITION_BY_PROJECTION_FILE[projection_file_position]

    base_directory: Path = Path(__file__).parent
    projection_path: Path = base_directory / PROJECTIONS_DIRECTORY_NAME /\
            PROJECTION_FILE_TEMPLATE.format(projection_file_position)

    players: list[Player] = []

    with open(projection_path, newline="", encoding="utf-8-sig") as projection_file:
        projection_rows = csv.reader(projection_file)
        header: list[str] = next(projection_rows)
        total_points_index: int = header.index("FPTS")

        for projection_row in projection_rows:
            # the exports carry a spacer row under the header and blank rows at the end
            if len(projection_row) <= total_points_index or not projection_row[0].strip():
                continue

            player_name: str = projection_row[0].strip()
            total_expected_points: float = float(projection_row[total_points_index])

            players.append(Player(player_name, position, total_expected_points / GAMES_PER_SEASON))

    return players


def read_all_projections() -> list[Player]:
    # a player listed in two files (a receiving back, say) is kept only at their better position
    players_by_name: dict[str, Player] = {}

    for projection_file_position in POSITION_BY_PROJECTION_FILE:
        for player in read_projection_file(projection_file_position):
            best_so_far: Player | None = players_by_name.get(player.name)

            if best_so_far is None or player.expected_gamely_score > best_so_far.expected_gamely_score:
                players_by_name[player.name] = player

    return list(players_by_name.values())


def read_player_csv() -> list[Player]:
    players: list[Player] = []

    base_directory: Path = Path(__file__).parent
    csv_path: Path = base_directory / "player_data.csv"

    player_data: list[str] = open(csv_path, "r", encoding="utf-8").read().split("\n")[1:-1]
    
    for player_datum in player_data:
        player_info: list[str] = player_datum.split(",")
        players.append(Player(player_info[0], player_info[1], float(player_info[2])))

    return sorted(players, key=lambda x: -x.expected_gamely_score)


def get_player_list() -> list[Player]:
    CSV_CURRENT: bool = True

    if CSV_CURRENT:
        return read_player_csv()

    players: list[Player] = read_all_projections()
    players.sort(key=lambda x: -x.expected_gamely_score)

    construct_player_csv(players)
    return players


def construct_player_csv(players: list[Player]) -> None:
    base_directory: Path = Path(__file__).parent
    csv_path: Path = base_directory / "player_data.csv"

    with open(csv_path, "w", encoding="utf-8") as writer:
        writer.write("name,position,expected gamely score\n")
        for player in players:
            writer.write(f"{player.name},{player.position},{player.expected_gamely_score:.4}\n")
