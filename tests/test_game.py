import unittest
import sys
import os
import random
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, rooms, Room, socketio
from game import Game, Role, Team, Player, GamePhase

class TestGame(unittest.TestCase):
    def setUp(self):
        """每个测试前的设置"""
        app.config['TESTING'] = True
        self.app = app.test_client()
        # 清空所有房间
        rooms.clear()
        self.test_room = None
        print(f"\n=== 开始测试: {self._testMethodName} ===")

    def tearDown(self):
        """每个测试后的清理"""
        if self.test_room and self.test_room.code in rooms:
            del rooms[self.test_room.code]
        print(f"=== 测试完成: {self._testMethodName} ===\n")

    def test_create_room(self):
        """测试创建房间"""
        print("测试创建房间...")
        
        # 创建5人房间
        host_name = "测试房主"
        player_count = 5
        room = Room(host_name, player_count)
        self.test_room = room
        rooms[room.code] = room

        # 验证房间创建
        self.assertIsNotNone(room.code)
        self.assertEqual(room.host_name, host_name)
        self.assertEqual(room.game.player_count, player_count)
        self.assertEqual(len(room.players), 1)
        print(f"房间创建成功: {room.code}")

    def test_join_room(self):
        """测试加入房间"""
        print("测试加入房间...")
        
        # 创建房间
        room = Room("测试房主", 5)
        self.test_room = room
        rooms[room.code] = room
        
        # 添加玩家
        test_players = ["测试玩家2", "测试玩家3", "测试玩家4", "测试玩家5"]
        for player_name in test_players:
            room.add_player(player_name)
            print(f"玩家 {player_name} 加入成功")

        # 验证玩家数量
        self.assertEqual(len(room.players), 5)
        print(f"当前玩家: {[p['name'] for p in room.players]}")

    def test_start_game(self):
        """测试开始游戏"""
        print("测试开始游戏...")
        
        # 创建并填满房间
        room = Room("测试房主", 5)
        self.test_room = room
        rooms[room.code] = room
        
        for i in range(2, 6):
            room.add_player(f"测试玩家{i}")

        # 开始游戏
        room.start_game()
        print("游戏开始")

        # 验证游戏状态
        self.assertTrue(room.game_started)
        self.assertEqual(room.game.current_phase, GamePhase.LEADER_TURN)
        
        # 检查角色分配
        roles = [player.role for player in room.game.players]
        teams = [player.team for player in room.game.players]
        
        print("\n角色分配:")
        for player in room.game.players:
            print(f"{player.name}: {player.role.display_name} ({player.team.display_name})")

        # 验证角色数量
        good_count = sum(1 for team in teams if team == Team.GOOD)
        evil_count = sum(1 for team in teams if team == Team.EVIL)
        print(f"\n阵营统计: 正义 {good_count}, 邪恶 {evil_count}")
        
        self.assertEqual(good_count, 3, "正义阵营应该有3人")
        self.assertEqual(evil_count, 2, "邪恶阵营应该有2人")

    def test_player_info_visibility(self):
        """测试玩家信息可见性"""
        print("测试玩家信息可见性...")
        
        # 创建并开始游戏
        room = Room("测试房主", 5)
        self.test_room = room
        rooms[room.code] = room
        
        for i in range(2, 6):
            room.add_player(f"测试玩家{i}")
        
        room.start_game()

        # 测试每个玩家的可见信息
        print("\n玩家可见信息测试:")
        for player in room.game.players:
            visible_info = room.game.get_player_info(player.name)
            print(f"\n{player.name} ({player.role.display_name}) 可见信息:")
            
            # 检查自己的信息
            self_info = next(info for info in visible_info if info['is_self'])
            self.assertEqual(self_info['role'], player.role.display_name)
            self.assertEqual(self_info['team'], player.team.value)
            
            # 打印可见的其他玩家信息
            for info in visible_info:
                if not info['is_self']:
                    team_info = info.get('team_display', '未知')
                    print(f"- 看到 {info['name']}: {team_info}")

    def test_quest_requirements(self):
        """测试任务需求"""
        print("测试任务需求...")
        
        # 测试不同人数的任务需求
        for player_count in range(5, 11):
            game = Game(player_count)
            requirements = game.quest_requirements
            print(f"\n{player_count}人局任务需求:")
            for quest_num, req in requirements.items():
                print(f"任务{quest_num}: {req}人")
            
            # 验证任务数量
            self.assertEqual(len(requirements), 5, f"{player_count}人局应该有5个任务")

    def test_create_and_join_flow(self):
        """测试创建房间和加入房间的完整流程"""
        print("\n=== 测试创建和加入房间流程 ===")
        
        # 1. 创建房间
        host_name = "测试房主"
        player_count = 5
        print(f"\n1. 创建{player_count}人房间")
        print(f"房主: {host_name}")
        
        room = Room(host_name, player_count)
        self.test_room = room
        rooms[room.code] = room
        
        print(f"房间创建成功: {room.code}")
        print(f"当前玩家: {[p['name'] for p in room.players]}")
        
        # 验证房间创建
        self.assertIsNotNone(room.code)
        self.assertEqual(room.host_name, host_name)
        self.assertEqual(room.game.player_count, player_count)
        self.assertEqual(len(room.players), 1)
        
        # 2. 其他玩家加入
        test_players = ["测试玩家2", "测试玩家3", "测试玩家4", "测试玩家5"]
        print("\n2. 其他玩家加入")
        
        for player_name in test_players:
            print(f"\n尝试加入玩家: {player_name}")
            try:
                room.add_player(player_name)
                print(f"玩家 {player_name} 加入成功")
            except Exception as e:
                print(f"玩家 {player_name} 加入失败: {str(e)}")
                raise
        
        # 验证玩家数量
        self.assertEqual(len(room.players), player_count)
        print(f"\n当前房间状态:")
        print(f"房间代码: {room.code}")
        print(f"玩家数量: {len(room.players)}/{room.game.player_count}")
        print(f"玩家列表: {[p['name'] for p in room.players]}")
        
        # 3. 开始游戏
        print("\n3. 开始游戏")
        try:
            room.start_game()
            print("游戏开始成功")
            
            # 验证游戏状态
            self.assertTrue(room.game_started)
            print("\n游戏状态:")
            print(f"阶段: {room.game.current_phase.value}")
            print(f"任务编号: {room.game.quest_number}")
            
            # 检查角色分配
            print("\n角色分配:")
            good_count = 0
            evil_count = 0
            for player in room.game.players:
                team = "正义" if player.team.value == 'GOOD' else "邪恶"
                if team == "正义":
                    good_count += 1
                else:
                    evil_count += 1
                print(f"{player.name}: {player.role.display_name} ({team}阵营)")
            
            print(f"\n阵营统计:")
            print(f"正义阵营: {good_count}人")
            print(f"邪恶阵营: {evil_count}人")
            
            # 验证阵营分配
            self.assertEqual(good_count, 3, "正义阵营应该有3人")
            self.assertEqual(evil_count, 2, "邪恶阵营应该有2人")
            
            # 4. 检查每个玩家的可见信息
            print("\n4. 检查信息可见性")
            for player in room.game.players:
                print(f"\n{player.name} ({player.role.display_name}) 可见信息:")
                visible_info = room.game.get_player_info(player.name)
                
                # 检查自己的信息
                self_info = next(info for info in visible_info if info['is_self'])
                print(f"自己的信息:")
                print(f"- 角色: {self_info['role']}")
                print(f"- 阵营: {self_info['team_display']}")
                
                # 检查其他玩家的可见信息
                print(f"其他玩家信息:")
                for info in visible_info:
                    if not info['is_self']:
                        team_info = info.get('team_display', '未知')
                        print(f"- {info['name']}: {team_info}")
        
        except Exception as e:
            print(f"游戏开始失败: {str(e)}")
            raise

def run_tests():
    """运行所有测试"""
    # 设置随机种子以保证测试结果可重现
    random.seed(datetime.now().timestamp())
    
    # 运行测试
    unittest.main(verbosity=2)

def run_specific_test():
    """运行特定测试"""
    suite = unittest.TestSuite()
    suite.addTest(TestGame('test_create_and_join_flow'))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)

if __name__ == '__main__':
    # 运行特定测试
    run_specific_test()