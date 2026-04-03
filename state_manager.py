from settings import STATE_MENU, STATE_PLAYING, STATE_GAME_OVER, STATE_ENDING


class StateManager:
    def __init__(self):
        self.state = STATE_MENU

    def set_menu(self) -> None:
        self.state = STATE_MENU

    def set_playing(self) -> None:
        self.state = STATE_PLAYING

    def set_game_over(self) -> None:
        self.state = STATE_GAME_OVER

    def set_ending(self) -> None:
        self.state = STATE_ENDING

    def is_menu(self) -> bool:
        return self.state == STATE_MENU

    def is_playing(self) -> bool:
        return self.state == STATE_PLAYING

    def is_game_over(self) -> bool:
        return self.state == STATE_GAME_OVER

    def is_ending(self) -> bool:
        return self.state == STATE_ENDING