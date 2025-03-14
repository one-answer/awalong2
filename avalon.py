import random
from typing import List, Dict

class AvalonGame:
    def __init__(self, player_count: int):
        if player_count < 5 or player_count > 10:
            raise ValueError("游戏人数必须在5-10人之间")
            
        self.player_count = player_count
        self.current_quest = 0
        self.quest_results = []
        self.leader_index = 0
        self.vote_track = 0
        self.quest_team = []
        
        # 设置每个任务需要的人数
        self.quest_requirements = {
            5: [2, 3, 2, 3, 3],
            6: [2, 3, 4, 3, 4],
            7: [2, 3, 3, 4, 4],
            8: [3, 4, 4, 5, 5],
            9: [3, 4, 4, 5, 5],
            10: [3, 4, 4, 5, 5]
        }
        
        # 根据玩家数量获取可用角色
        self.roles = {
            5: ["梅林", "刺客", "爪牙", "派西维尔", "忠臣"],
            6: ["梅林", "刺客", "爪牙", "派西维尔", "忠臣", "忠臣"],
            7: ["梅林", "刺客", "爪牙", "派西维尔", "忠臣", "忠臣", "忠臣"],
            8: ["梅林", "刺客", "爪牙", "爪牙", "派西维尔", "忠臣", "忠臣", "忠臣"],
            9: ["梅林", "刺客", "爪牙", "爪牙", "派西维尔", "忠臣", "忠臣", "忠臣", "忠臣"],
            10: ["梅林", "刺客", "爪牙", "爪牙", "派西维尔", "忠臣", "忠臣", "忠臣", "忠臣", "忠臣"]
        }
        
        # 初始化玩家列表，但不分配角色
        self.players = [(f"玩家{i+1}", None) for i in range(player_count)]
        self.roles_assigned = False

    def assign_roles(self):
        """在所有玩家加入后分配角色"""
        if self.roles_assigned:
            return
        
        available_roles = self.roles[self.player_count].copy()
        random.shuffle(available_roles)
        self.players = [(name, available_roles[i]) for i, (name, _) in enumerate(self.players)]
        self.roles_assigned = True
        
    def get_quest_requirement(self) -> int:
        return self.quest_requirements[self.player_count][self.current_quest]
        
    def propose_team(self, leader: int, team: List[int]) -> bool:
        if len(team) != self.get_quest_requirement():
            return False
        
        self.quest_team = team
        return True
        
    def team_vote(self, votes: List[bool]) -> bool:
        if len(votes) != self.player_count:
            return False
            
        approve_count = sum(1 for v in votes if v)
        if approve_count > len(votes) // 2:
            self.vote_track = 0
            if not self.quest_team:
                return False
            return True
        
        self.vote_track += 1
        if self.vote_track == 5:
            # 如果连续5次提议都被否决，邪恶方获胜
            return False
            
        self.leader_index = (self.leader_index + 1) % self.player_count
        self.quest_team = []  # 清空队员列表
        return False
        
    def quest_vote(self, votes: List[bool]) -> bool:
        if len(votes) != len(self.quest_team):
            return False
            
        fail_count = sum(1 for v in votes if not v)
        quest_success = fail_count == 0  # 第4轮任务特殊规则：8-10人时需要2个失败才算失败
        if self.player_count >= 7 and self.current_quest == 3:
            quest_success = fail_count < 2
            
        self.quest_results.append(quest_success)
        self.current_quest += 1
        self.leader_index = (self.leader_index + 1) % self.player_count
        return quest_success
        
    def check_game_state(self) -> tuple[bool, str]:
        success_count = sum(1 for r in self.quest_results if r)
        fail_count = len(self.quest_results) - success_count
        
        if success_count >= 3:
            return True, "正义方获胜！（除非刺客成功刺杀梅林）"
        elif fail_count >= 3:
            return True, "邪恶方获胜！"
        
        return False, "游戏继续"

def play_game():
    print("\n=== 角色说明 ===")
    print("正义方：")
    print("- 梅林：知道所有邪恶方成员，但不能明显表现出来，否则会被刺客刺杀")
    print("- 忠臣：为了亚瑟王的正义而战，要帮助好人赢得任务")
    print("\n邪恶方：")
    print("- 刺客：邪恶方首领，如果正义方赢得3次任务，有一次机会刺杀梅林")
    print("- 爪牙：莫德雷德的爪牙，要帮助邪恶方获胜")
    print("\n=== 游戏规则 ===")
    print("1. 每轮任务队长选择队员")
    print("2. 所有人投票是否同意这个队伍")
    print("3. 获得过半数同意后，队员秘密投票任务成功或失败")
    print("4. 任意一方先赢得3次任务即可获胜")
    print("5. 正义方胜利后，刺客有一次机会刺杀梅林")
    print("6. 连续5次队伍提议被否决，邪恶方直接获胜")
    print("================\n")

    # 获取玩家数量
    while True:
        try:
            player_count = int(input("请输入玩家数量 (5-10): "))
            game = AvalonGame(player_count)
            break
        except ValueError as e:
            print(e)
            continue
    
    # 显示每个玩家的角色
    for i, (player, role) in enumerate(game.players):
        input(f"请让 {player} 查看角色 (按回车继续)")
        print(f"你的角色是: {role}")
        if role == "梅林":
            evil_players = [f"玩家{j+1}" for j, (_, r) in enumerate(game.players) 
                          if r in ["刺客", "爪牙"]]
            print(f"你看到的邪恶方玩家是: {', '.join(evil_players)}")
        elif role in ["刺客", "爪牙"]:
            evil_players = [f"玩家{j+1}" for j, (_, r) in enumerate(game.players) 
                          if r in ["刺客", "爪牙"]]
            print(f"你的邪恶同伴是: {', '.join(evil_players)}")
        print("\n" * 50)  # 清屏
    
    # 游戏主循环
    while True:
        print(f"\n当前任务: {game.current_quest + 1}")
        print(f"任务结果: {''.join('成功' if r else '失败' for r in game.quest_results)}")
        print(f"需要 {game.get_quest_requirement()} 人参加任务")
        print(f"当前队长: 玩家{game.leader_index + 1}")
        
        # 队长选择队伍
        while True:
            try:
                team_input = input("队长请选择队员 (用空格分隔的数字，如: 1 2 3): ")
                team = [int(x) - 1 for x in team_input.split()]
                if game.propose_team(game.leader_index, team):
                    break
                print("无效的队伍选择，请重试")
            except ValueError:
                print("输入格式错误，请重试")
        
        # 所有玩家投票
        print("\n=== 队伍投票环节 ===")
        votes = []
        for i in range(game.player_count):
            while True:
                vote = input(f"玩家{i+1} 请投票 (同意Y/反对N): ").upper()
                if vote in ['Y', 'N']:
                    votes.append(vote == 'Y')
                    break
                print("请输入 Y 或 N")
        
        if not game.team_vote(votes):
            print("队伍被否决！")
            continue
        
        # 任务执行
        print("\n=== 任务执行环节 ===")
        quest_votes = []
        for player_index in team:
            while True:
                vote = input(f"玩家{player_index + 1} 请为任务投票 (成功S/失败F): ").upper()
                if vote in ['S', 'F']:
                    quest_votes.append(vote == 'S')
                    break
                print("请输入 S 或 F")
        
        success = game.quest_vote(quest_votes)
        print("任务成功！" if success else "任务失败！")
        
        # 检查游戏状态
        game_over, message = game.check_game_state()
        if game_over:
            print(message)
            if "正义方获胜" in message:
                # 刺客猜测梅林
                assassin_guess = int(input("刺客，请猜测谁是梅林 (输入玩家编号): ")) - 1
                merlin_index = next(i for i, (_, role) in enumerate(game.players) if role == '梅林')
                if assassin_guess == merlin_index:
                    print("刺客成功刺杀梅林！邪恶方获胜！")
                else:
                    print("刺客猜错了！正义方获胜！")
            break

if __name__ == "__main__":
    print("欢迎来到阿瓦隆！")
    play_game() 