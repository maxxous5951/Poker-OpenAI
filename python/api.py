import os
import openai
#from colorama import init
import traceback
#import debugpy
#import pydevd_pycharm

from python.audio_player           import AudioPlayer
from python.hero_info              import HeroInfo
from python.hero_hand_range        import PokerHandRangeDetector
from python.game_state             import GameState
#from hero_action            import HeroAction
from python.poker_assistant        import PokerAssistant
from python.gui                    import GUI
from python.set_table_datas        import SetTableDatas

class Api:

    def __init__( self, oh ):
        #debugpy.listen(("localhost", 5678))  # Open a debug port
        #debugpy.wait_for_client()  # Pause execution until debugger is attached
        #pydevd_pycharm.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True)

        self.oh                      = oh
        self.api_key                 = os.getenv('OPENAI_API_KEY')
        self.openai_client           = openai.OpenAI(api_key=self.api_key)
        #init(autoreset=True)

        # Initialize all the instances

        self.audio_player            = AudioPlayer( self.openai_client )
        
        self.hero_info               = HeroInfo()
        self.hero_hand_range         = PokerHandRangeDetector()

        self.game_state              = GameState( self.audio_player )
        self.poker_assistant         = PokerAssistant( self.openai_client, self.hero_info, self.game_state, self.audio_player )
       
        self.gui                     = GUI( self.game_state, self.poker_assistant )
        self.table_data_setter       = SetTableDatas( self.oh, self.hero_info, self.hero_hand_range, self.poker_assistant, self.game_state )
       

        #setup_read_poker_table( read_poker_table=read_poker_table )

        # Update hero player number in game state
        #game_state.update_player(hero_player_number, hero=True)

        #game_state.hero_player_number = hero_player_number

        #game_state.extract_blinds_from_title()

        # Start the GUI
        self.gui.run()

        

    def set_table_datas(self):

        self.table_data_setter.set_table_datas()


    def reset_on_handreset(self):

        self.table_data_setter.reset_table_datas()