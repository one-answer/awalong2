import unittest
from app import Room, Player
from game import Game, GamePhase, Quest, Role, Team
from enum import Enum

class Team(Enum):
    GOOD = "正义"
    EVIL = "邪恶"

class Role(Enum):
    LOYAL_SERVANT = ('亚瑟的忠臣', Team.GOOD, '效忠于亚瑟王的正义骑士')
    DUKE = ('公爵', Team.GOOD, '在最终任务中可以指定一位玩家放下一只手')
    GRAND_DUKE = ('大公', Team.GOOD, '在最终任务中，邪恶方揭露身份后，可以改变一个玩家一只手的指向')
    MORGAN = ('摩根勒菲', Team.EVIL, '不受魔法指示物效果影响，可以出任务失敗牌')
    PRINCE = ('王儲', Team.EVIL, '不知道邪恶方有谁，但邪恶方知道谁是王儲')
    SHAPESHIFTER = ('幻形妖', Team.EVIL, '邪恶方不知道幻形妖是谁，幻形妖也不知道哪些人是邪恶方')
    MORDRED_MINION = ('莫德雷德的爪牙', Team.EVIL, '知道其他邪恶阵营的人（除了幻形妖）')

    def __init__(self, display_name, team, description):
        self.display_name = display_name
        self.team = team
        self.description = description

class TestGameFlow(unittest.TestCase):
    def setUp(self):
        """设置测试环境"""
        # 创建一个5人房间
        self.room = Room("玩家1", 5)
        
        # 添加其他玩家
        self.room.add_player("玩家2")
        self.room.add_player("玩家3")
        self.room.add_player("玩家4")
        self.room.add_player("玩家5")

    def test_game_flow(self):
        """测试完整游戏流程"""
        print("\n=== 开始游戏流程测试 ===")
        
        # 1. 测试房间创建
        print("\n1. 测试房间创建")
        self.assertEqual(len(self.room.players), 5)
        self.assertEqual(self.room.host_name, "玩家1")
        print(f"房间创建成功，房间号: {self.room.code}")
        print(f"玩家列表: {[p.name for p in self.room.players]}")
        
        # 2. 开始游戏
        print("\n2. 开始游戏")
        self.room.start_game()
        self.assertIsNotNone(self.room.game)
        print("游戏开始成功")
        
        # 3. 测试角色分配
        print("\n3. 角色分配")
        good_count = 0
        evil_count = 0
        
        for player in self.room.game.players:
            if hasattr(player, 'role'):
                team = player.role.team
                print(f"[DEBUG] Player {player.name} role: {player.role.display_name}, team: {team}")
                if team == Team.GOOD:
                    good_count += 1
                elif team == Team.EVIL:
                    evil_count += 1
                print(f"玩家 {player.name}: 角色 - {player.role.display_name}, 阵营 - {team.value}")
                print(f"角色描述: {player.role.description}")
        
        print(f"\n[DEBUG] Raw team counts - Good: {good_count}, Evil: {evil_count}")
        print(f"\n阵营统计: 好人 {good_count}, 坏人 {evil_count}")
        
        # 验证每个角色的阵营
        for role in Role:
            print(f"[DEBUG] Role {role.display_name} is on team {role.team}")
        
        # 4. 测试任务流程
        for quest_num in range(1, 4):
            print(f"\n4.{quest_num} 第{quest_num}轮任务")
            
            # 4.1 队长选择队员
            current_leader = self.room.game.get_current_leader()
            required_players = self.room.game.current_quest.required_players
            selected_team = self.room.game.players[:required_players]
            
            self.room.game.current_quest.team = selected_team
            print(f"队长 {current_leader.name} 选择队员: {[p.name for p in selected_team]}")
            
            # 4.2 任务投票
            votes_result = {}
            for player in selected_team:
                # 根据阵营决定投票
                success = True if player.role.team == Team.GOOD else False
                votes_result[player.name] = success
                print(f"玩家 {player.name} 投票: {'成功' if success else '失败'}")
            
            self.room.game.current_quest.votes = votes_result
            
            # 4.3 计算任务结果
            fail_votes = sum(1 for vote in votes_result.values() if not vote)
            quest_success = fail_votes == 0
            self.room.game.quest_results.append(quest_success)
            
            if quest_success:
                self.room.game.successful_quests += 1
            else:
                self.room.game.failed_quests += 1
            
            print(f"任务结果: {'成功' if quest_success else '失败'}")
            print(f"当前战况: 成功 {self.room.game.successful_quests} vs 失败 {self.room.game.failed_quests}")
            
            # 4.4 准备下一轮
            if quest_num < 3:
                self.room.game.prepare_next_quest()
                print(f"准备第 {quest_num + 1} 轮任务")
        
        # 5. 验证游戏结果
        print("\n5. 游戏结束")
        total_quests = self.room.game.successful_quests + self.room.game.failed_quests
        self.assertEqual(total_quests, 3)
        print(f"最终战况: 成功 {self.room.game.successful_quests} vs 失败 {self.room.game.failed_quests}")
        winner = "好人阵营" if self.room.game.successful_quests >= 3 else "坏人阵营"
        print(f"胜利方: {winner}")

if __name__ == '__main__':
    unittest.main(verbosity=2) 