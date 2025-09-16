from pathlib import Path

class Player:
    def __init__(self, name: str, position: str, expected_gamely_score: float):
        self.name: str = name
        self.position: str = position
        self.expected_gamely_score: float = expected_gamely_score

    def __str__(self) -> str:
        return f"{self.position} {self.name} with expected score {self.expected_gamely_score:.4}"
    

def get_player_raw_data() -> list[str]:
    base_directory: Path = Path(__file__).parent
    raw_data_path: Path = base_directory / "player_data_raw.txt"

    return open(raw_data_path, encoding="utf-8").read().lower().split("\n")


def construct_player(player_info_lines: list[str], root_player_index: int) -> Player:
    player_name = player_info_lines[root_player_index + 4].title()
    player_position = player_info_lines[root_player_index + 5][-2:].upper()

    expected_points_index = player_info_lines.index("2025 outlook:", root_player_index) - 1
    total_expected_points = float(player_info_lines[expected_points_index])
    expected_gamely_score = total_expected_points / 17

    return Player(player_name, player_position, expected_gamely_score)


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
    
    players: list[Player] = []

    player_info_lines: list[str] = get_player_raw_data()

    last_player_index = 0
    while "rank" in player_info_lines[last_player_index:]:
        root_player_index = player_info_lines.index("rank", last_player_index)
        players.append(construct_player(player_info_lines, root_player_index))

        last_player_index = root_player_index + 1

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

