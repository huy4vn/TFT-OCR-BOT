"""
Handles tasks that happen each game round
"""

from time import sleep, perf_counter
import random
import multiprocessing
import win32gui
import settings
import game_assets
import game_functions
import arena_functions
from arena import Arena
from vec4 import Vec4
from vec2 import Vec2
from comps import CompsManager

class Game:
    """Game class that handles game logic such as round tasks"""

    def __init__(self, message_queue: multiprocessing.Queue, comps : CompsManager) -> None:
        self.message_queue = message_queue
        self.comps_manager = comps
        self.arena = Arena(self.message_queue, comps)
        self.round = "0-0"
        self.time: None = None
        self.forfeit_time: int = settings.FORFEIT_TIME + random.randint(50, 150)
        self.found_window = False

        print("\n[!] Searching for game window")
        while not self.found_window:
            print("  Did not find window, trying again...")
            win32gui.EnumWindows(self.callback, None)
            sleep(1)

        self.loading_screen()

    def callback(self, hwnd, extra) -> None:  # pylint: disable=unused-argument
        """Function used to find the game window and get its size"""
        if "League of Legends (TM) Client" not in win32gui.GetWindowText(hwnd):
            return

        rect = win32gui.GetWindowRect(hwnd)

        x_pos = rect[0]
        y_pos = rect[1]
        width = rect[2] - x_pos
        height = rect[3] - y_pos

        if width < 200 or height < 200:
            return

        print(f"  Window {win32gui.GetWindowText(hwnd)} found")
        print(f"    Location: ({x_pos}, {y_pos})")
        print(f"    Size:     ({width}, {height})")
        Vec4.setup_screen(x_pos, y_pos, width, height)
        Vec2.setup_screen(x_pos, y_pos, width, height)
        self.found_window = True

    def loading_screen(self) -> None:
        """Loop that runs while the game is in the loading screen"""
        game_functions.default_pos()
        while game_functions.get_round() != "1-1":
            sleep(1)
        self.start_time: float = perf_counter()
        self.game_loop()

    def game_loop(self) -> None:
        """Loop that runs while the game is active, handles calling the correct tasks for round and exiting game"""
        ran_round: str = None
        while game_functions.check_alive():
            self.round: str = game_functions.get_round()

            if (
                settings.FORFEIT
                and perf_counter() - self.start_time > self.forfeit_time
            ):
                game_functions.forfeit()
                return

            if self.round != ran_round:
                print(f"\n[Comps] Stick to [{','.join(self.comps_manager.CURRENT_COMP()[1])}] ")
                if self.round in game_assets.CAROUSEL_ROUND:
                    self.carousel_round()
                    ran_round: str = self.round
                elif self.round in game_assets.PVE_ROUND:
                    game_functions.default_pos()
                    self.pve_round()
                    ran_round: str = self.round
                elif self.round in game_assets.PVP_ROUND:
                    game_functions.default_pos()
                    self.pvp_round()
                    ran_round: str = self.round
            sleep(0.5)
        self.message_queue.put("CLEAR")
        game_functions.exit_game()
        game_functions.victory_exit()

    def carousel_round(self) -> None:
        """Handles tasks for carousel rounds"""
        print(f"\n[Carousel Round] {self.round}")
        self.message_queue.put("CLEAR")
        if self.round == "3-4":
            self.arena.final_comp = True
        self.arena.check_health()
        print("  Getting a champ from the carousel")
        game_functions.get_champ_carousel(self.round)
        game_functions.default_pos()

    def pve_round(self) -> None:
        """Handles tasks for PVE rounds"""
        print(f"\n[PvE Round] {self.round}")
        self.message_queue.put("CLEAR")
        sleep(0.5)
        if self.round in game_assets.AUGMENT_ROUNDS:
            sleep(1)
            self.arena.pick_augment()
            # Can't purchase champions for a short period after choosing augment
            sleep(2.5)
        if self.round == "1-3":
            sleep(1.5)
            self.arena.fix_unknown()
            self.arena.tacticians_crown_check()
        elif self.round == "4-7":
            game_functions.select_shop()

        self.arena.fix_bench_state()
        self.arena.spend_gold()
        self.arena.move_champions()
        self.arena.replace_unknown()
        if self.arena.final_comp:
            self.arena.final_comp_check()
        self.arena.bench_cleanup()
        self.end_round_tasks()

    def pvp_round(self) -> None:
        """Handles tasks for PVP rounds"""
        print(f"\n[PvP Round] {self.round}")
        self.message_queue.put("CLEAR")
        sleep(0.5)
        if self.round in game_assets.AUGMENT_ROUNDS:
            sleep(1)
            self.arena.pick_augment()
            sleep(2.5)
        if self.round in ("2-1"):
            """Level to 5 at 2-5"""
            self.arena.buy_xp_round()
            print(f"\n[LEVEL UP] Lvl. {arena_functions.get_level()}")
        if self.round in ("2-5"):
            """Level to 5 at 2-5"""
            while arena_functions.get_level() < 5:
                self.arena.buy_xp_round()
            else:
                print(f"\n[LEVEL UP] Lvl. {arena_functions.get_level()}")
        if self.round in ("3-2"):
            """Level to 6 at 3-2"""
            while arena_functions.get_level() < 6:
                self.arena.buy_xp_round()
            else:
                print(f"\n[LEVEL UP] Lvl. {arena_functions.get_level()}")
        if self.round in ("4-1"):
            """Level to 7 at 4-1"""
            while arena_functions.get_level() < 7:
                self.arena.buy_xp_round()
            else:
                print(f"\n[LEVEL UP] Lvl. {arena_functions.get_level()}")
        if self.round in ("5-1"):
            """Level to 8 at 5-1"""
            while arena_functions.get_level() < 8:
                self.arena.buy_xp_round()
            else:
                print(f"\n[LEVEL UP] Lvl. {arena_functions.get_level()}")
        if self.round in game_assets.PICKUP_ROUNDS:
            print("  Picking up items")
            game_functions.pickup_items()

        self.arena.fix_bench_state()
        self.arena.bench_cleanup()
        if self.round in game_assets.ANVIL_ROUNDS:
            self.arena.clear_anvil()
        self.arena.spend_gold()
        self.arena.move_champions()
        self.arena.replace_unknown()
        if self.arena.final_comp:
            self.arena.final_comp_check()
        self.arena.bench_cleanup()

        if self.round in game_assets.ITEM_PLACEMENT_ROUNDS:
            sleep(1)
            self.arena.place_items()
        self.end_round_tasks()

    def end_round_tasks(self) -> None:
        """Common tasks across rounds that happen at the end"""
        self.arena.check_health()
        self.arena.get_label()
        game_functions.default_pos()