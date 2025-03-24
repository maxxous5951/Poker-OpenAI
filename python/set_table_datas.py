from colorama import Fore
import re
import numpy as np
import time
from datetime import datetime

import threading
from threading import Lock


class SetTableDatas:

    def __init__( self, oh, hero_info, hero_hand_range, poker_assistant, game_state ):

        self.game_state_lock        = Lock()  # Initialize the lock for game_state

        self.hero_info              = hero_info

        self.hero_hand_range        = hero_hand_range

        self.poker_assistant        = poker_assistant

        self.game_state             = game_state

        self.oh                     = oh

        #self.save_screenshots       = False

        #self.tesseract_cmd          = r'C:\Projects\PokerGPT\tesseract\tesseract.exe'

        #self.cards_on_table         = False

        #self.previous_hashes        = {}  # Dictionary to store previous hashes for each player

        #self.photo                  = None

        self.last_active_player     = 1  # Default to player 1 or any other suitable default

        self.last_action_player     = 0  # For detecting player actions and stack sizes only once

        self.hero_buttons_active    = self.get_hero_buttons()  # Detected active hero buttons

        self.shutdown_flag = threading.Event()

        self.threads = []
    


    def get_hero_buttons(self):

        hero_buttons = {"actions": []}
        hero_button_bits = self.oh["myturnbits"]

        # Action bits dictionary
        actions_map = {
            0x01: "Fold",
            0x02: "Call",
            0x04: "Check",
            0x08: "Raise",
            0x10: "All-in"
        }

        # Vérification des bits actifs et ajout des actions correspondantes
        # Check of active bits to fill hero_buttons
        hero_buttons["actions"] = [action for bit, action in actions_map.items() if hero_button_bits & bit]

        return hero_buttons
    


    def analyze_and_log(self):
        
        action_result = self.poker_assistant.AnalyzeAI(self.hero_buttons_active, self.game_state.get_ai_log())

        print(f"{Fore.CYAN}self.poker_assistant.AnalyzeAI RESULT: {action_result}")

        if action_result is not None:
            self.game_state.add_log_entry({'method': 'update_hero_action',
                'Action':       action_result['Action'],
                'Amount':       action_result['Amount'],
                'Tactic':       action_result['Tactic'],
                'Strategy':     action_result['Strategy'],
                'Explanation':  action_result['Explanation']
            })

            self.hero_info.add_strategy(action_result['Strategy'])
            self.hero_info.add_tactic(action_result['Tactic'])
            self.hero_info.update_action_count(self.game_state.round_count, self.game_state.players[self.game_state.hero_player_number].get('role'),
                                            self.game_state.current_board_stage, 
                                            action_result['Action'])
        


    def update_player_active_state(self, player_number):

        current_status = self.game_state.players.get(player_number, {}).get('status')
        isactive = (((self.oh["playersactivebits"] >> player_number) & 1) == 0)

        if isactive:
            # Update player status to inactive
            current_status == 'Active'
        else:
            current_status == 'Inactive'
        
        with self.game_state_lock:  
            self.game_state.update_player(player_number, status='Inactive')



    def set_won_amount(self):         
        """
        Set won amounts.
        """
        for player_number, player_info in self.game_state.players.items():
            if player_info['stack_size'] > player_info['previous_stack_size']:
                won_amount_number = player_info['stack_size'] - player_info['previous_stack_size']
                
                self.game_state.update_player(player_number, stack_size=player_info['stack_size'], won_amount=won_amount_number)
                self.last_action_player = player_number

            player_info['previous_stack_size'] = player_info['stack_size']
        

    def set_betround(self):
        """
        Set the bet round.
        """   
        with self.game_state_lock:
            self.game_state.update_board_stage(self.oh["betround"])
        

    def set_hero_position(self):
        """
        Set the hero position.
        """

        with self.game_state_lock:                 
            self.game_state.update_player_hero(self.oh["userchair"])   
            self.game_state.hero_player_number = self.oh["userchair"]
        

    def set_dealer_position(self):
        """
        Set the dealer position.
        """

        with self.game_state_lock:                   
            self.game_state.update_dealer_position(self.oh["dealerchair"])
            self.game_state.dealer_position = self.oh["dealerchair"] 
        

    def set_active_players(self):
        """
        Set active players.
        """
        
        for player_number in self.game_state.players.items():
            self.update_player_active_state(player_number)

    def set_blinds(self):
        """
        Set the blinds.
        """

        self.game_state.small_blind = self.oh["sblind"]
        self.game_state.big_blind = self.oh["bblind"]
        
        print(f"Small Blind: ${self.game_state.small_blind}, Big Blind: ${self.game_state.big_blind}")

        #with self.game_state_lock:
        #    self.game_state.update_blinds(self.oh["sblind"], self.oh["bblind"])
        

    def set_total_pot(self):
        """
        Set the total pot.
        """
        for player_number, player_info in self.game_state.players.items():
            player_info['pot_size'] = self.oh["pot"]

        with self.game_state_lock:          
            self.game_state.update_total_pot(self.oh["pot"])        
            self.game_state.total_pot = self.oh["pot"]
        

    def set_players_stack_size(self):
        """
        Set the players stack size.
        """
        for player_number, player_info in self.game_state.players.items():
            player_info['stack_size'] = self.oh["balance" + player_number]
        

    def reset_players_action(self):
        """
        Reset the players action.
        """
        for player_number, player_info in self.game_state.players.items():
            player_info['action'] = None
            player_info['amount'] = None
        

    def set_players_action(self):
        """
        Set the players action.
        """
        self.reset_players_action()
        start_chair = 0
        if self.oh["betround"] ==  1:
            if not self.oh["missingsmallblind"] and self.oh["currentbet" + self.oh["smallblindchair"]] == self.oh["sblind"]  and self.oh["currentbet" + self.oh["biglindchair"]] == self.oh["bblind"]:
                start_chair = self.oh["biglindchair"] + 1
            elif self.oh["missingsmallblind"] and self.oh["currentbet" + self.oh["biglindchair"]] == self.oh["bblind"]:
                start_chair = (self.oh["biglindchair"] + 1) % self.oh["nchairs"]
            else:
                start_chair = self.oh["dealerchair"] + 1
        else:
            start_chair = self.oh["dealerchair"] + 1 

        for player_number in range(start_chair, self.game_state.players.items()):
            chair_ndx = player_number % self.oh["nchairs"]
            if chair_ndx == self.oh["userchair"]:
                break
            biggest_betsize = 0
            did_bet = False
            if self.oh["betround"] ==  1:
                if not self.oh["missingsmallblind"] and self.oh["currentbet" + self.oh["smallblindchair"]] == self.oh["sblind"]  and self.oh["currentbet" + self.oh["biglindchair"]] == self.oh["bblind"]:
                    biggest_betsize = self.oh["bblind"]
                elif self.oh["missingsmallblind"] and self.oh["currentbet" + self.oh["biglindchair"]] == self.oh["bblind"]:
                    biggest_betsize = self.oh["bblind"]
            if self.oh["currentbet" + chair_ndx] < biggest_betsize:
                self.player_info['action'] = "Fold"
                self.last_action_player = chair_ndx
            elif self.oh["currentbet" + chair_ndx] == biggest_betsize == 0:
                self.player_info['action'] = "Check"
                self.last_action_player = chair_ndx
            elif self.oh["currentbet" + chair_ndx] == biggest_betsize != 0:
                self.player_info['action'] = "Call"
                self.last_action_player = chair_ndx
            elif self.oh["currentbet" + chair_ndx] > biggest_betsize:
                if did_bet:
                    self.player_info['action'] = "Raise"
                    self.player_info['amount'] = self.oh["currentbet" + chair_ndx]
                    self.last_action_player = chair_ndx
                    biggest_betsize = self.oh["currentbet" + chair_ndx]
                else:
                    self.player_info['action'] = "Bet"
                    self.player_info['amount'] = self.oh["currentbet" + chair_ndx]
                    self.last_action_player = chair_ndx
                    biggest_betsize = self.oh["currentbet" + chair_ndx]
                    did_bet = True
        

    def RankNumberToRankCharacter(self, rank):
        """
        Get rank character from rank number.
        """
        ranks = {
            2: "2",
            3: "3",
            4: "4",
            5: "5",
            6: "6",
            7: "7",
            8: "8",
            9: "9",
            10: "T",
            11: "J",
            12: "Q",
            13: "K",
            14: "A"
        }
        return ranks.get(rank, None)
        

    def SuitNumberToSuitCharacter(self, suit):
        """
        Get suit character from suit number.
        """
        suits = {
            0: "h",
            1: "d",
            2: "c",
            3: "s"
        }
        return suits.get(suit, None)
        

    def set_hero_cards(self):
        """
        Set hero cards.
        """
        rank0 = self.RankNumberToRankCharacter(self.oh["$$pr0"])
        suit0 = self.SuitNumberToSuitCharacter(self.oh["$$ps0"])
        rank1 = self.RankNumberToRankCharacter(self.oh["$$pr1"])
        suit1 = self.SuitNumberToSuitCharacter(self.oh["$$ps1"])
        self.game_state.players[self.oh["userchair"]]["cards"] = [(rank0 + suit0), (rank1 + suit1)]

        #print(f"{Fore.RED}-------------------------------------------------------")
        #print(f"{Fore.RED}self.hero_buttons_active = {self.hero_buttons_active}")
        #print(f"{Fore.RED}-------------------------------------------------------")

        #time.sleep(0.2)
                
        if self.game_state.round_count > 0:
                    
            if self.game_state.current_board_stage == 'Pre-Flop':

                hero_role   = self.game_state.players[self.game_state.hero_player_number].get('role')
                hero_cards = self.game_state.players[self.game_state.hero_player_number].get('cards')

                print(F"{Fore.RED} HERO CARDS: {hero_cards}")

                is_playable_card = False

                if hero_cards:
                    is_playable_card = self.hero_hand_range.is_hand_in_range(hero_cards) 

                if is_playable_card:

                    analysis_thread = threading.Thread(target=self.analyze_and_log)
                    analysis_thread.start()
                    print(F"{Fore.GREEN} PLAYABLE CARD: {hero_cards} in {hero_role} ROLE")

                else:
                    #self.hero_action.execute_action(None,"Fold", None)  ==> turn it to getDecision('Fold')
                    self.game_state.update_player(self.game_state.hero_player_number, action='Fold')

                    self.hero_info.update_action_count(self.game_state.round_count, self.game_state.players[self.game_state.hero_player_number].get('role'),
                                    self.game_state.current_board_stage, 
                                    'Fold')
                            
                    print(F"{Fore.RED} UNPLAYABLE CARD: {hero_cards} in {hero_role} ROLE ")
                            

            else:
                analysis_thread = threading.Thread(target=self.analyze_and_log)
                analysis_thread.start()
        

    def set_community_cards(self):
        """
        Set community cards.
        """
        if self.oh["betround"] == 1 :
            return
        elif self.oh["betround"] > 1 :
            rank0 = self.RankNumberToRankCharacter(self.oh["$$cr0"])
            suit0 = self.SuitNumberToSuitCharacter(self.oh["$$cs0"])
            rank1 = self.RankNumberToRankCharacter(self.oh["$$cr1"])
            suit1 = self.SuitNumberToSuitCharacter(self.oh["$$cs1"])
            rank2 = self.RankNumberToRankCharacter(self.oh["$$cr2"])
            suit2 = self.SuitNumberToSuitCharacter(self.oh["$$cs2"])
            if self.oh["betround"] == 2 :
                self.game_state.update_community_cards([(rank0 + suit0), (rank1 + suit1), (rank2 + suit2)])
            elif self.oh["betround"] == 3 :
                rank3 = self.RankNumberToRankCharacter(self.oh["$$cr3"])
                suit3 = self.SuitNumberToSuitCharacter(self.oh["$$cs3"])
                self.game_state.update_community_cards([(rank0 + suit0), (rank1 + suit1), (rank2 + suit2), (rank3 + suit3)])
            #elif self.oh["betround"] == 4 :
            else:
                rank4 = self.RankNumberToRankCharacter(self.oh["$$cr4"])
                suit4 = self.SuitNumberToSuitCharacter(self.oh["$$cs4"])
                self.game_state.update_community_cards([(rank0 + suit0), (rank1 + suit1), (rank2 + suit2), (rank3 + suit3), (rank4 + suit4)])



    def set_table_datas(self):
        self.set_betround()
        self.set_hero_position()
        self.set_dealer_position()
        self.set_active_players()
        self.set_blinds()
        self.set_total_pot()
        self.set_players_stack_size()
        self.set_won_amount()
        self.set_players_action()
        self.set_community_cards()
        #self.set_hero_cards_combination()
        self.set_hero_cards()


    def reset_table_datas(self):
        
        with self.game_state_lock:

            self.game_state.update_dealer_position(self.oh["dealerchair"])                    
            self.game_state.dealer_position = self.oh["dealerchair"]

            if self.game_state.round_count > 1:
                if self.game_state.round_count % 12 == 0: #Do every 8 rounds
                    # Start a new thread for player analysis
                    analysis_thread = threading.Thread(target=self.poker_assistant.analyze_players_gpt4, args=(self.game_state.all_round_logs,))
                    analysis_thread.start()
                                
            self.game_state.reset_for_new_round() # THIS MUST BE AFTER analyze_players_gpt4() function so it doesn reset data before Analysis!
                      


    