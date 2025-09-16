from strategy_common import *


def get_player_from_input(available_players: list[Player], given_input: str) -> Player | None:
    try:
        given_position: str = given_input.split(" ")[0].upper()
        given_double_initials: str = given_input.split(" ")[1].upper()

        entry_intention_map: dict[str, str] = {"K": "SK", "D": "AR", "D/ST": "AR", "DST": "AR"}
        if given_position in entry_intention_map:
            given_position = entry_intention_map[given_position]

        for player in available_players:
            player_double_initials: str = "".join(name[0:2] for name in player.name.split(" "))
            if player_double_initials.upper() == given_double_initials and player.position == given_position:
                return player
            
    except Exception:
        return None
    

def get_base_positions() -> list[str]:
    positions: list[str] = []
    for position in POSITION_NUM_MAPPING.keys():
        if position not in ("FLEX", "BENCH"):
            positions.append(position)

    return positions


def drafting_backups(drafter: DraftedTeam) -> bool:
    for position in ("QB", "WR", "RB", "TE", "FLEX"):
        if len(drafter.get_players_at_position(position)) < POSITION_NUM_MAPPING[position]:
            return False
        
    return True


def backups_likelihood(drafter: DraftedTeam) -> dict[str, float]:
    total_caps: dict[str, int] = {"QB": 3, "WR": 7, "RB": 6, "TE": 3, "AR": 2, "SK": 2}
    picks_left_by_position: dict[str, int] = {}

    for position, cap in total_caps.items():
        picks_left_by_position[position] = max(cap - len(drafter.get_players_at_position(position)), 0)

    total_needed: int = sum(picks_left_by_position.values())

    return {position: picks_left_by_position[position] / total_needed for position in total_caps}


def get_likelihood_each_position_taken(drafter: DraftedTeam, print_debug = False) -> dict[str, float]:
    positions: list[str] = get_base_positions()

    if drafting_backups(drafter):
        if print_debug:
            print(f"{drafter.drafter_name} drafting backups")

        return backups_likelihood(drafter)

    drafter_team_state: dict[str, int] = {}

    for position in positions:
        drafter_team_state[position] = len(drafter.get_players_at_position(position))
    
    POSITION_IMPORTANCES: dict[str, float] = {"QB": 1.25, "WR": 1.5, "RB": 1.5, "TE": .75, "AR": .001, "SK": .001}

    need_by_position: dict[str, float] = {}
    for position in positions:
        need_by_position[position] = max((POSITION_NUM_MAPPING[position] - drafter_team_state[position])\
                * POSITION_IMPORTANCES[position], 0)
        
    if drafter.get_players_at_position("FLEX") == []:
        for flex_position in FLEX_POSITIONS:
            if need_by_position[flex_position] == 0:
                # give a bit of need if can be drafted at FLEX, even if otherwise full
                flex_importances: dict[str, float] = {"WR": .8, "RB": .4, "TE": .05}
                need_by_position[flex_position] = POSITION_IMPORTANCES[flex_position] * flex_importances[flex_position]

    total_need: float = sum(need_by_position.values())
    if total_need == 0:
        return {position: 0 for position in get_base_positions()}

    likelihood_each_position_taken: dict[str, float] = {position: need_by_position[position] / total_need\
                                                        for position in positions}
    
    if print_debug:
        print(f"{drafter.drafter_name} has {drafter_team_state} so they take "
            f"{[[position, round(likelihood, 4)] for position, likelihood in likelihood_each_position_taken.items()]}")
        
    return likelihood_each_position_taken


def update_position_distribution_single(position_distribution: dict[str, dict[int, float]], drafter: DraftedTeam,
                                        second: bool = False, weight: float = 1, print_debug: bool = False) -> None:
    likelihood_each_position_taken: dict[str, float] = get_likelihood_each_position_taken(drafter,
                                                       print_debug and (not second))

    drafter_copy: DraftedTeam = DraftedTeam("", drafter.strategy)

    for position in position_distribution:
        likelihood_position_taken = likelihood_each_position_taken[position]
        if likelihood_position_taken == 0 or weight == 0:
            continue

        max_taken_before: int = max(position_distribution[position].keys())

        for times_taken in range(max_taken_before + 1, 0, -1):
            added_probability: float = position_distribution[position][times_taken - 1] *\
                    likelihood_position_taken * weight
            if added_probability < 0.00001:
                continue

            if times_taken == max_taken_before + 1:
                position_distribution[position][times_taken] = 0

            position_distribution[position][times_taken] += added_probability
            position_distribution[position][times_taken - 1] -= added_probability

    if not second:
        for position in position_distribution:
            drafter_copy.players = drafter.players[:] + [Player("", position, 0)]
            update_position_distribution_single(position_distribution, drafter_copy,
                                                True, likelihood_each_position_taken[position])


def update_position_distribution(position_distribution: dict[str, dict[int, float]],
                                drafters_between: list[DraftedTeam], print_debug = False) -> None:
    for drafter in drafters_between:
        update_position_distribution_single(position_distribution, drafter, print_debug=print_debug)



# TESTING FUNCTIONS
def test_update_position_distribution(position_distribution: dict[str, dict[int, float]],
                                drafters_between: list[DraftedTeam], print_debug = False) -> None:
    for drafter in drafters_between:
        test_update_position_distribution_single(position_distribution, drafter, print_debug=print_debug)

def test_update_position_distribution_single(position_distribution: dict[str, dict[int, float]], drafter: DraftedTeam,
                                        second: bool = False, weight: float = 1, print_debug: bool = False) -> None:
    likelihood_each_position_taken: dict[str, float] = test_get_likelihood_each_position_taken(drafter,
                                                       print_debug and (not second))

    drafter_copy: DraftedTeam = DraftedTeam("", drafter.strategy)

    for position in position_distribution:
        likelihood_position_taken = likelihood_each_position_taken[position]
        if likelihood_position_taken == 0 or weight == 0:
            continue

        max_taken_before: int = max(position_distribution[position].keys())

        for times_taken in range(max_taken_before + 1, 0, -1):
            added_probability: float = position_distribution[position][times_taken - 1] *\
                    likelihood_position_taken * weight
            if added_probability < 0.00001:
                continue

            if times_taken == max_taken_before + 1:
                position_distribution[position][times_taken] = 0

            position_distribution[position][times_taken] += added_probability
            position_distribution[position][times_taken - 1] -= added_probability

    if not second:

        for position in position_distribution:
            drafter_copy.players = drafter.players[:] + [Player("", position, 0)]
            new_distribution: dict[str, float] = get_likelihood_each_position_taken(drafter_copy)
            test_update_position_distribution_single(position_distribution, drafter_copy,
                                                True, likelihood_each_position_taken[position])
            
def test_get_likelihood_each_position_taken(drafter: DraftedTeam, print_debug = False) -> dict[str, float]:
    positions: list[str] = get_base_positions()

    if drafting_backups(drafter):
        if print_debug:
            print(f"{drafter.drafter_name} drafting backups")
        return {"QB": 1/7, "WR": 2.8/7, "RB": 2.2/7, "TE": 1/7, "AR": .001, "SK": .001}

    drafter_team_state: dict[str, int] = {}

    for position in positions:
        drafter_team_state[position] = len(drafter.get_players_at_position(position))
    
    POSITION_IMPORTANCES: dict[str, float] = {"QB": 1.25, "WR": 1.5, "RB": 1.5, "TE": .75, "AR": .2, "SK": .2}

    need_by_position: dict[str, float] = {}
    for position in positions:
        need_by_position[position] = max((POSITION_NUM_MAPPING[position] - drafter_team_state[position])\
                * POSITION_IMPORTANCES[position], 0)
        
    if drafter.get_players_at_position("FLEX") == []:
        for flex_position in FLEX_POSITIONS:
            if need_by_position[flex_position] == 0:
                flex_importances: dict[str, float] = {"WR": .8, "RB": .4, "TE": .05}
                # give a bit of need if can be drafted at FLEX, even if otherwise full
                need_by_position[flex_position] = POSITION_IMPORTANCES[flex_position] * flex_importances[flex_position]

    total_need: float = sum(need_by_position.values())
    if total_need == 0:
        return {position: 0 for position in get_base_positions()}

    likelihood_each_position_taken: dict[str, float] = {position: need_by_position[position] / total_need\
                                                        for position in positions}
    
    if print_debug:
        print(f"{drafter.drafter_name} has {drafter_team_state} so they take "
            f"{[[position, round(likelihood, 4)] for position, likelihood in likelihood_each_position_taken.items()]}")
        
    return likelihood_each_position_taken