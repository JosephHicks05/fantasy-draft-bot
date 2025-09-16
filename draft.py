from players import Player, get_player_list
from strategy import DraftedTeam, DraftStrategy, get_strategy, POSITION_NUM_MAPPING, ALL_STRATEGIES, FLEX_POSITIONS

NUM_DRAFT_ROUNDS: int = sum(POSITION_NUM_MAPPING.values())
AUTO_STRATEGY: DraftStrategy = get_strategy("manual_predictive")

class Draft:
    def __init__(self, auto_init = False):
        self.print_picks: bool = not auto_init
        self.teams: list[DraftedTeam] = []
        self.current_drafter_index: int = 0
        self.current_round_number: int = 0
        self.available_players: list[Player] = get_player_list()

        if not auto_init:
            manual_assignment: bool = input("manually assign strategies? (y/n): ").lower() in ("y", "yes")
            self.num_drafters: int = int(input("how many drafters are there? "))
            self.draft_position: int = -1 if manual_assignment else int(input("what is your draft position? "))

            self._assign_names()

            if manual_assignment:
                self._assign_strategies()


    def run_draft(self) -> None:
        while not self._draft_completed():
            self._perform_next_pick()


    def print_results(self) -> None:
        self._sort_teams()
        print("\nresults:")

        for rank, team in enumerate(self.teams, 1):
            print(f"rank {rank}: {team.drafter_name}, expected {team.expected_gamely_score():.5}"
                    " per week. They drafted:")
            
            for player in team.players:
                print(f"{player.position} {player.name} (expected {player.expected_gamely_score} per week)")
            print()


    def available_at_position(self, position: str) -> list[Player]:
        players: list[Player] = []

        for player in self.available_players:
            if player.position == position or (position == "FLEX" and player.position in FLEX_POSITIONS):
                players.append(player)

            if len(players) > 30:
                return players

        return players
    

    def current_drafter(self) -> DraftedTeam:
        return self.teams[self.current_drafter_index]
    
    
    def picks_until_next(self) -> int:
        if self.snaking_forward():
            return (self.num_drafters - self.current_drafter_index - 1) * 2
        else:
            return self.current_drafter_index * 2


    def _draft_completed(self) -> bool:
        return self.current_round_number >= NUM_DRAFT_ROUNDS


    def _assign_strategies(self):
        for drafter in self.teams:
            request_prompt: str = f"what strategy should {drafter.drafter_name} use? (options are "
            for strategy in ALL_STRATEGIES:
                request_prompt += f"{strategy.name}, "
            while True:
                try:
                    selected_strategy: str = input(request_prompt[:-2] + "): ")
                    drafter.strategy = get_strategy(selected_strategy)
                    break
                except ValueError as error:
                    print(error)


    def _assign_names(self):
        for drafter_index in range(1, self.num_drafters+1):
            if drafter_index == self.draft_position:
                self.teams.append(DraftedTeam("You", AUTO_STRATEGY))
            else:
                drafter_name: str = input(f"What is the name of drafter number {drafter_index}? ")
                self.teams.append(DraftedTeam(drafter_name, get_strategy("manual")))


    def _perform_next_pick(self) -> None:
        drafter: DraftedTeam = self.teams[self.current_drafter_index]
        selected_player: Player = drafter.strategy.strategy(self)

        self.available_players.remove(selected_player)
        drafter.players.append(selected_player)

        self._advance_pick_number()

        if not self.print_picks:
            return

        select_conjugation: str = "should select" if (drafter.drafter_name == "You"\
                and not drafter.strategy == get_strategy("manual_predictive")) else "selected"
        print(f"{drafter.drafter_name} {select_conjugation} {selected_player.position} {selected_player.name}.\n")


    def snaking_forward(self) -> bool:
        return self.current_round_number % 2 == 0


    def _advance_pick_number(self) -> None:
        if self.snaking_forward() and self.current_drafter_index == self.num_drafters - 1:
            self.current_round_number += 1
        
        elif self.snaking_forward():
            self.current_drafter_index += 1

        elif self.current_drafter_index == 0:
            self.current_round_number += 1

        else:
            self.current_drafter_index -= 1

    def _sort_teams(self) -> None:
        self.teams.sort(key=lambda x: -x.expected_gamely_score())



class AutoDraft(Draft):
    def __init__(self, testing_strategy: DraftStrategy, others_strategy: DraftStrategy, 
                num_drafters: int, testing_positon: int):
        super().__init__(True)
        self.testing_strategy: DraftStrategy = testing_strategy
        self.num_drafters = num_drafters

        for drafter_index in range(self.num_drafters):
            strategy: DraftStrategy = testing_strategy if drafter_index == testing_positon else others_strategy
            self.teams.append(DraftedTeam("guy " + str(drafter_index + 1), strategy))
    

    def get_tested_position(self) -> int:
        self._sort_teams()
        for drafter_index in range(self.num_drafters):
            if self.teams[drafter_index].strategy == self.testing_strategy:
                return drafter_index
            
        raise ValueError(f"test strategy {self.testing_strategy.name} not found")
    

def get_average_result(testing_strategy: DraftStrategy, others_strategy: DraftStrategy, num_drafters: int) -> float:
    results: list[int] = []

    for testing_position in range(num_drafters):
        draft: AutoDraft = AutoDraft(testing_strategy, others_strategy, num_drafters, testing_position)

        draft.print_picks = False
        draft.run_draft()
        results.append(draft.get_tested_position())

    print(results)
    return (sum(results) / len(results)) + 1



def run_draft() -> None:
    draft: Draft = Draft()

    draft.run_draft()

    draft.print_results()


if __name__ == "__main__":
    run_draft()
    #print(get_average_result(get_strategy("test"), get_strategy("predictive"), 10))
    # draft: AutoDraft = AutoDraft(get_strategy("predictive"), get_strategy("volatile"), 10, 4)
    # draft.print_picks = True
    # draft.run_draft()
    # draft.print_results()

  