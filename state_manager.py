from settings import STATE_MENU, STATE_CONTROLS, STATE_SETTINGS, STATE_PLAYING, STATE_PAUSE, STATE_TRANSITION, STATE_GAME_OVER, STATE_ENDING


class StateManager:
    def __init__(self):
        self.state = STATE_MENU

    def set_menu(self) -> None:
        self.state = STATE_MENU

    def set_controls(self) -> None:
        self.state = STATE_CONTROLS

    def set_settings(self) -> None:
        self.state = STATE_SETTINGS

    def set_playing(self) -> None:
        self.state = STATE_PLAYING

    def set_pause(self) -> None:
        self.state = STATE_PAUSE

    def set_transition(self) -> None:
        self.state = STATE_TRANSITION

    def set_game_over(self) -> None:
        self.state = STATE_GAME_OVER

    def set_ending(self) -> None:
        self.state = STATE_ENDING

    def is_menu(self) -> bool:
        return self.state == STATE_MENU

    def is_controls(self) -> bool:
        return self.state == STATE_CONTROLS

    def is_settings(self) -> bool:
        return self.state == STATE_SETTINGS

    def is_playing(self) -> bool:
        return self.state == STATE_PLAYING

    def is_pause(self) -> bool:
        return self.state == STATE_PAUSE

    def is_transition(self) -> bool:
        return self.state == STATE_TRANSITION

    def is_game_over(self) -> bool:
        return self.state == STATE_GAME_OVER

    def is_ending(self) -> bool:
        return self.state == STATE_ENDING