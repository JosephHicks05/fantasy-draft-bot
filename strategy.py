from strategy_common import *
from strategy_utils import *
from scipy.stats import binom
from functools import lru_cache


def pick_best_player(draft: "Draft") -> Player:
    return draft.available_players[0]


def allow_player_pick(draft: "Draft") -> Player:
    drafter: DraftedTeam = draft.current_drafter()

    while True:
        selection: Player | None = get_player_from_input(draft.available_players, input(
                f"enter {drafter.drafter_name} pick {draft.current_round_number+1}"
                " <position> <initials>: "))
        
        if selection is None:
            print("could not find a player of that position with those initials. Try again.")
        else:
            break

    return selection


def pick_best_player_vacant_position(draft: "Draft") -> Player:
    drafter: DraftedTeam = draft.current_drafter()

    non_full_positions: set[str] = drafter.get_non_full_positions()

    pick_candidates: list[Player] = []

    for position in non_full_positions:
        pick_candidates.extend(draft.available_at_position(position))
    
    pick_candidates.sort(key=player_expected_score)

    if pick_candidates == []:
        return pick_best_player(draft)
    else:
        return pick_candidates[0]
    

@lru_cache(maxsize=None)
def binom_quantile(percentile: float, trials: int, trial_proportion: float):
    return int(binom.ppf(percentile, trials, trial_proportion))
    

def pick_most_volatile_position(draft: "Draft") -> Player:
    PRINT_DEBUG_INFO: bool = False
    drafter: DraftedTeam = draft.current_drafter()

    non_full_positions: list[str] = list(drafter.get_non_full_positions())

    if non_full_positions == []:
        return pick_best_player(draft)
    
    #TODO fix flex. shouldn't draft two TE
    if drafter.get_players_at_position("FLEX") == []:
        for position in FLEX_POSITIONS:
            if len(drafter.get_players_at_position(position)) == POSITION_NUM_MAPPING[position]:
                non_full_positions.remove(position)
                if "FLEX" not in non_full_positions:
                    non_full_positions.append("FLEX")

    best_player_by_position: dict[str, Player] = {}
    for position in non_full_positions:
        if position == "FLEX":
            available_flex_players: list[Player] = []
            for flex_position in FLEX_POSITIONS:
                if len(drafter.get_players_at_position(flex_position)) == POSITION_NUM_MAPPING[flex_position]:
                    available_flex_players.extend(draft.available_at_position(flex_position))

            available_flex_players.sort(key=player_expected_score)
            best_player_by_position[position] = available_flex_players[0]
            continue

        best_player_by_position[position] = draft.available_at_position(position)[0]

    proportion_positions_taken: dict[str, float] = {"QB": .175, "RB": .35, "WR": .35, "TE": .15, "SK": .07, "AR": .07}
    best_player_by_position_next: dict[str, Player] = {}
    picks_until_next: int = draft.picks_until_next()
    picks_until_next = picks_until_next if picks_until_next != 0 else draft.num_drafters - 1

    times_flex_positions_picked: dict[str, int] = {}
    for flex_position in FLEX_POSITIONS:
        proportion_position_taken: float = proportion_positions_taken[flex_position]
        times_flex_positions_picked[flex_position] = binom_quantile(.5, picks_until_next, proportion_position_taken)

    for position in non_full_positions:
        if position == "FLEX":
            pre_available_flex_players: list[Player] = []
            for flex_position in FLEX_POSITIONS:
                if len(drafter.get_players_at_position(flex_position)) == POSITION_NUM_MAPPING[flex_position]:
                    times_flex_position_picked = times_flex_positions_picked[flex_position]
                    pre_available_flex_players += draft.available_at_position(flex_position)[times_flex_position_picked:]

            pre_available_flex_players.sort(key=player_expected_score)
            
            best_player_by_position_next[position] = pre_available_flex_players[0]
            continue


        proportion_position_taken: float = proportion_positions_taken[position]
        times_position_picked: int = binom_quantile(.5, picks_until_next, proportion_position_taken)
        if position in FLEX_POSITIONS:
            times_flex_positions_picked[position] = times_position_picked

        best_player_after_picks: Player = draft.available_at_position(position)[times_position_picked]
        best_player_by_position_next[position] = best_player_after_picks

    value_lost_by_position: dict[str, float] = {}
    for position in non_full_positions:
        value_lost_by_position[position] = best_player_by_position[position].expected_gamely_score\
                - best_player_by_position_next[position].expected_gamely_score
    
    most_volatile_position = sorted(value_lost_by_position.items(), key=lambda item: -item[1])[0][0]

    if PRINT_DEBUG_INFO:
        print(list(map(lambda x: x[1].name, best_player_by_position.items())))
        print(list(map(lambda x: x[1].name, best_player_by_position_next.items())))
        print(list(map(lambda x: (x[0], round(x[1], 3)), value_lost_by_position.items())))
        if "FLEX" in non_full_positions:
            print([player.name for player in available_flex_players[:8]]) # type: ignore

    return best_player_by_position[most_volatile_position]


def pick_volatile_position_predictive(draft: "Draft") -> Player:
    PRINT_DEBUG_INFO: bool = False
    drafter: DraftedTeam = draft.current_drafter()
    base_positions: list[str] = get_base_positions()
    
    num_positions_picked_distribution: dict[str, dict[int, float]] = {}
    for position in base_positions:
        num_positions_picked_distribution[position] = {0: 1}

    if draft.snaking_forward():
        players_between_picks: list[DraftedTeam] = draft.teams[draft.current_drafter_index + 1:]
    else:
        players_between_picks: list[DraftedTeam] = draft.teams[:draft.current_drafter_index]

    if players_between_picks == []:
        players_between_picks = draft.teams[:]
        players_between_picks.remove(drafter)

    if PRINT_DEBUG_INFO:
        print(f"{[team.drafter_name for team in players_between_picks]} going next")

    update_position_distribution(num_positions_picked_distribution, players_between_picks, PRINT_DEBUG_INFO)

    if PRINT_DEBUG_INFO:
        print([(position, [(num, round(proportion, 4))for num, proportion in distribution.items()])
               for position, distribution in num_positions_picked_distribution.items()])
        
    expected_loss_by_position: dict[str, float] = {}
    for position in base_positions:
        expected_loss_by_position[position] = 0
        players_at_position: list[Player] = draft.available_at_position(position)
        best_player_position_skill = players_at_position[0].expected_gamely_score
        position_picked_distribution = num_positions_picked_distribution[position]

        for pick_number_possibility, likelihood in position_picked_distribution.items():
            that_player_skill = players_at_position[pick_number_possibility].expected_gamely_score

            expected_loss_by_position[position] += (best_player_position_skill - that_player_skill) * likelihood

    
    non_full_positions: set[str] = drafter.get_non_full_positions()

    #TODO make work with flex better
    for bad_flex_position in ("TE", "RB"):
        if drafter.get_players_at_position("FLEX") == [] and\
                len(drafter.get_players_at_position(bad_flex_position)) == POSITION_NUM_MAPPING[bad_flex_position] and\
                draft.available_at_position(bad_flex_position)[0].expected_gamely_score\
                < draft.available_at_position("WR")[0].expected_gamely_score:
            non_full_positions.remove(bad_flex_position)


    for position in expected_loss_by_position:
        if len(drafter.get_players_at_position(position)) == POSITION_NUM_MAPPING[position] - 1\
                and not drafting_backups(drafter):
            expected_loss_by_position[position] -= .2

    print([(position, round(loss, 4)) for position, loss in expected_loss_by_position.items()])

    for position in base_positions:
        if position not in non_full_positions and not drafting_backups(drafter):
            del expected_loss_by_position[position]

    if expected_loss_by_position == {}:
        return pick_best_player(draft)

    most_volatile_position: str = sorted(expected_loss_by_position.items(), key=lambda x: -x[1])[0][0]
    return draft.available_at_position(most_volatile_position)[0]
    

def testing_strategy_1(draft: "Draft") -> Player:
    PRINT_DEBUG_INFO: bool = True
    drafter: DraftedTeam = draft.current_drafter()
    base_positions: list[str] = get_base_positions()
    
    num_positions_picked_distribution: dict[str, dict[int, float]] = {}
    for position in base_positions:
        num_positions_picked_distribution[position] = {0: 1}

    if draft.snaking_forward():
        players_between_picks: list[DraftedTeam] = draft.teams[draft.current_drafter_index + 1:]
    else:
        players_between_picks: list[DraftedTeam] = draft.teams[:draft.current_drafter_index]

    if players_between_picks == []:
        players_between_picks = draft.teams[:]
        players_between_picks.remove(drafter)

    if PRINT_DEBUG_INFO:
        #print(f"{[team.drafter_name for team in players_between_picks]} going next")
        pass

    test_update_position_distribution(num_positions_picked_distribution, players_between_picks, PRINT_DEBUG_INFO)

    if PRINT_DEBUG_INFO:
        # print([(position, [(num, round(proportion, 4))for num, proportion in distribution.items()])
        #        for position, distribution in num_positions_picked_distribution.items()])
        pass

    expected_loss_by_position: dict[str, float] = {}
    for position in base_positions:
        expected_loss_by_position[position] = 0
        players_at_position: list[Player] = draft.available_at_position(position)
        best_player_position_skill = players_at_position[0].expected_gamely_score
        position_picked_distribution = num_positions_picked_distribution[position]

        for pick_number_possibility, likelihood in position_picked_distribution.items():
            that_player_skill = players_at_position[pick_number_possibility].expected_gamely_score

            expected_loss_by_position[position] += (best_player_position_skill - that_player_skill) * likelihood

    
    non_full_positions: set[str] = drafter.get_non_full_positions()

    #TODO make work with flex better
    for bad_flex_position in ("TE", "RB"):
        if drafter.get_players_at_position("FLEX") == [] and\
                len(drafter.get_players_at_position(bad_flex_position)) == POSITION_NUM_MAPPING[bad_flex_position] and\
                draft.available_at_position(bad_flex_position)[0].expected_gamely_score\
                < draft.available_at_position("WR")[0].expected_gamely_score:
            non_full_positions.remove(bad_flex_position)


    for position in base_positions:
        if position not in non_full_positions:
            del expected_loss_by_position[position]

    if expected_loss_by_position == {}:
        return pick_best_player(draft)
    
    for position in expected_loss_by_position:
        if len(drafter.get_players_at_position(position)) == POSITION_NUM_MAPPING[position] - 1:
            expected_loss_by_position[position] -= .2

    if PRINT_DEBUG_INFO:
        print([(position, round(loss, 4)) for position, loss in expected_loss_by_position.items()])
    
    most_volatile_position: str = sorted(expected_loss_by_position.items(), key=lambda x: -x[1])[0][0]
    return draft.available_at_position(most_volatile_position)[0]


def manual_predictive(draft: "Draft") -> Player:
    suggested_player: Player = pick_volatile_position_predictive(draft)
    print(f"you should pick {suggested_player.position} {suggested_player.name}")
    return allow_player_pick(draft)


ALL_STRATEGIES: list[DraftStrategy] = [DraftStrategy("greedy", pick_best_player),
                                       DraftStrategy("manual", allow_player_pick),
                                       DraftStrategy("greedy_vacant", pick_best_player_vacant_position),
                                       DraftStrategy("volatile", pick_most_volatile_position),
                                       DraftStrategy("predictive", pick_volatile_position_predictive),
                                       DraftStrategy("manual_predictive", manual_predictive),
                                       DraftStrategy("test", testing_strategy_1)]

def get_strategy(name: str) -> DraftStrategy:
    for strategy in ALL_STRATEGIES:
        if name == strategy.name:
            return strategy
        
    raise ValueError(f"{name} is not the name of a strategy.")