#!/usr/bin/env python
# -*- coding: utf-8 -*-

from game import Game, Team, GamePhase, Player, FinalQuestStatus
import random
import time

class GameRunner:
    def __init__(self):
        self.game = None
        
    def start_new_game(self):
        """开始新游戏"""
        print("欢迎来到阿瓦隆Quest！")
        
        # 获取玩家数量
        while True:
            try:
                player_count = int(input("请输入玩家数量 (4-10): "))
                if 4 <= player_count <= 10:
                    break
                print("玩家数量必须在4-10之间")
            except ValueError:
                print("请输入有效数字")
        
        self.game = Game(player_count)
        
        # 添加玩家
        for i in range(player_count):
            name = input("请输入玩家{0}的名字: ".format(i+1))
            self.game.add_player(name)
        
        # 开始游戏
        self.game.start_game()
        self.run_game_loop()
        
    def run_game_loop(self):
        """运行游戏主循环"""
        while not self.game.is_game_over():
            print("\n" + "="*50)
            print(self.game.get_game_status())
            print(self.game.get_timer_status())
            
            if self.game.current_phase == GamePhase.LEADER_TURN:
                self.handle_leader_turn()
            elif self.game.current_phase == GamePhase.QUEST:
                self.handle_quest_phase()
            elif self.game.current_phase == GamePhase.FINAL_QUEST:
                self.handle_final_quest()
                
            time.sleep(1)  # 防止刷屏太快
            
        self.show_game_result()
        
    def handle_leader_turn(self):
        """处理领袖回合"""
        leader = self.game.get_current_leader()
        print("\n当前领袖: {0}".format(leader.name))
        required_players = self.game.get_current_quest_size()
        print("需要选择 {0} 名队员".format(required_players))
        print("当前是第 {0} 个任务".format(self.game.quest_number))
        
        while not (self.game.current_quest and self.game.current_quest.is_team_full()):
            # 显示当前已选择的队员
            current_team = self.game.current_quest.team if self.game.current_quest else []
            if current_team:
                print("\n已选择的队员: {0}".format(", ".join(p.name for p in current_team)))
                print("还需要选择 {0} 名队员".format(required_players - len(current_team)))
            
            print("\n可选玩家:")
            for i, player in enumerate(self.game.players):
                status = " (已选择)" if player in current_team else ""
                print("{0}. {1}{2}".format(i+1, player.name, status))
                
            try:
                choice = int(input("\n请选择队员 (输入序号): ")) - 1
                if 0 <= choice < len(self.game.players):
                    selected_player = self.game.players[choice]
                    if selected_player in current_team:
                        print("\n错误: {0} 已经在队伍中了".format(selected_player.name))
                    else:
                        self.game.assign_quest_member(leader, selected_player)
                        print("\n成功选择: {0}".format(selected_player.name))
                else:
                    print("\n无效的选择")
            except ValueError:
                print("\n请输入有效数字")
            except Exception as e:
                print("\n错误: {0}".format(e))
            
            # 添加一个空行使输出更清晰
            print("")
            
    def handle_quest_phase(self):
        """处理任务阶段"""
        if not self.game.current_quest:
            return
            
        print("\n任务执行阶段")
        print("当前队员:", ", ".join(p.name for p in self.game.current_quest.team))
        
        for player in self.game.current_quest.team:
            if any(r.player == player for r in self.game.current_quest.results):
                continue
                
            print(f"\n{player.name} 的回合")
            if player.magic_tokens > 0:
                use_magic = input("是否使用魔法指示物? (y/n): ").lower() == 'y'
            else:
                use_magic = False
                
            if player.team == Team.EVIL:
                success = input("选择任务结果 (s:成功/f:失败): ").lower() == 's'
            else:
                success = True
                
            self.game.submit_quest_result(player, success, use_magic)
            
    def handle_final_quest(self):
        """处理最终任务"""
        if not self.game.final_quest:
            self.game.start_final_quest()
            return
            
        print("\n最终任务阶段")
        print(self.game.get_final_quest_status())
        
        if self.game.final_quest.status == FinalQuestStatus.SELECTING_LEADER:
            self.handle_final_leader_selection()
        elif self.game.final_quest.status == FinalQuestStatus.SELECTING_TEAM:
            self.handle_final_team_selection()
        elif self.game.final_quest.status == FinalQuestStatus.EXECUTING:
            self.handle_final_quest_execution()
            
    def show_game_result(self):
        """显示游戏结果"""
        print("\n" + "="*50)
        print(self.game.get_game_summary())
        
        print("\n玩家统计:")
        for player in self.game.players:
            print("\n" + "-"*30)
            print(self.game.get_player_stats(player))
            
    def handle_final_leader_selection(self):
        """处理最终任务领袖选择"""
        if not self.game.final_quest.nominated_leader:
            good_players = [p for p in self.game.players if p.team == Team.GOOD]
            print("\n正义阵营玩家可以提名领袖:")
            for i, player in enumerate(self.game.players):
                print(f"{i+1}. {player.name}")
                
            try:
                choice = int(input("请选择要提名的领袖 (输入序号): ")) - 1
                if 0 <= choice < len(self.game.players):
                    nominator = random.choice(good_players)
                    self.game.nominate_final_leader(nominator, self.game.players[choice])
                else:
                    print("无效的选择")
            except ValueError:
                print("请输入有效数字")
            except Exception as e:
                print(f"错误: {e}")
        else:
            # 处理投票
            for player in self.game.players:
                if player not in self.game.final_quest.votes:
                    print(f"\n{player.name} 请为 {self.game.final_quest.nominated_leader.name} 投票")
                    approve = input("同意这位领袖吗? (y/n): ").lower() == 'y'
                    self.game.vote_for_final_leader(player, approve)
                    
    def handle_final_team_selection(self):
        """处理最终任务队伍选择"""
        leader = self.game.final_quest.nominated_leader
        print(f"\n领袖 {leader.name} 选择队员")
        self.handle_leader_turn()  # 复用普通任务的队员选择逻辑
        
    def handle_final_quest_execution(self):
        """处理最终任务执行"""
        print("\n最终任务执行")
        self.handle_quest_phase()  # 复用普通任务的执行逻辑

if __name__ == "__main__":
    runner = GameRunner()
    runner.start_new_game() 