from __future__ import annotations  # 添加这行来支持前向引用
from enum import Enum, auto
from typing import List, Dict, Optional, Set, Callable
import random
from datetime import datetime, timedelta
import time

class Team(Enum):
    GOOD = "GOOD"
    EVIL = "EVIL"

    @property
    def display_name(self):
        return {
            'GOOD': '正义阵营',
            'EVIL': '邪恶阵营'
        }[self.value]

    @property
    def value(self):
        return self.name

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

class GamePhase(Enum):
    SETUP = 'SETUP'
    LEADER_TURN = 'LEADER_TURN'
    TEAM_VOTE = 'TEAM_VOTE'
    QUEST_VOTE = 'QUEST_VOTE'
    SELECT_NEXT_LEADER = 'SELECT_NEXT_LEADER'
    GAME_OVER = 'GAME_OVER'

class Player:
    def __init__(self, name: str):
        if not name.strip():
            raise ValueError("玩家名称不能为空")
        self.name = name.strip()
        self.role = None
        self.team = None
        self.magic_tokens = 0  # 初始没有魔法指示物
        self.amulets = 1
        self.revealed_by_amulet = []
    
    def use_magic_token(self) -> bool:
        """使用魔法指示物强制任务成功"""
        if self.magic_tokens > 0:
            self.magic_tokens -= 1
            return True
        return False
    
    def use_amulet(self) -> bool:
        """使用护身符查验玩家阵营"""
        if self.amulets > 0:
            self.amulets -= 1
            return True
        return False

    def was_revealed_by(self, player: Player) -> bool:
        """检查是否被指定玩家查验过"""
        return player in self.revealed_by_amulet
        
    def add_revealer(self, player: Player):
        """添加查验者记录"""
        if player not in self.revealed_by_amulet:
            self.revealed_by_amulet.append(player)

    def to_dict(self):
        """将Player对象转换为字典"""
        return {
            'name': self.name,
            'role': self.role.display_name if self.role else None,
            'team': self.team.value if self.team else None,
            'magic_tokens': self.magic_tokens,
            'amulets': self.amulets
        }

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        if isinstance(other, Player):
            return self.name == other.name
        return False

class SpecialAbility(Enum):
    NONE = auto()                    # 无特殊能力
    SEE_EVIL = auto()                # 看到邪恶玩家
    PREDICT_QUEST = auto()           # 预知任务结果
    PROTECT_PLAYER = auto()          # 保护玩家
    STEAL_MAGIC = auto()             # 窃取魔法指示物
    SABOTAGE_QUEST = auto()          # 干扰任务
    FAKE_IDENTITY = auto()           # 伪装身份
    KNOW_EVIL_TEAM = auto()          # 知晓邪恶阵营

class AbilityUse:
    def __init__(self, user: Player, ability: SpecialAbility, target: Optional[Player] = None):
        self.user = user
        self.ability = ability
        self.target = target
        self.timestamp = datetime.now()
        self.quest_number: Optional[int] = None

class QuestResult:
    def __init__(self, success: bool, player: Player, used_magic: bool = False):
        self.success = success
        self.player = player
        self.used_magic = used_magic

class Quest:
    def __init__(self, quest_number: int, required_players: int):
        self.quest_number = quest_number
        self.required_players = required_players
        self.team = []
        self.results = []
        self.is_completed = False
        self.votes = {}  # 存储任务投票结果 {player_name: success}
        self.vote_track = 0
        self.result = None

    def add_team_member(self, player: Player):
        """添加任务队员"""
        if len(self.team) >= self.required_players:
            raise ValueError("任务队员已满")
        if player in self.team:
            raise ValueError("该玩家已经在任务队伍中")
        self.team.append(player)

    def is_team_full(self) -> bool:
        """检查任务队伍是否已满"""
        return len(self.team) == self.required_players

    def submit_result(self, player: Player, success: bool, used_magic: bool = False):
        """提交任务结果"""
        if player not in self.team:
            raise ValueError("只有任务队员才能提交结果")
        if any(r.player == player for r in self.results):
            raise ValueError("该玩家已经提交过结果")
        self.results.append(QuestResult(success, player, used_magic))

    def get_final_result(self) -> bool:
        """获取任务最终结果"""
        if not self.is_completed:
            raise ValueError("任务尚未完成")
        return all(result.success for result in self.results)

    def complete_quest(self):
        """完成任务并返回结果"""
        if len(self.votes) < len(self.team):
            raise ValueError("还有队员未投票")
        
        fail_votes = sum(1 for vote in self.votes.values() if not vote)
        self.result = fail_votes == 0
        return self.result, fail_votes

class AmuletResult:
    def __init__(self, target_player: Player, revealed_team: Team, is_true_team: bool):
        self.target_player = target_player
        self.revealed_team = revealed_team  # 显示的阵营
        self.is_true_team = is_true_team    # 是否是真实阵营

class AmuletUse:
    def __init__(self, user: Player, target: Player):
        self.user = user
        self.target = target
        self.result: Optional[AmuletResult] = None
        self.timestamp = None  # 用于记录使用时间

class FinalQuestStatus(Enum):
    NOT_STARTED = "未开始"
    SELECTING_LEADER = "选择领袖"
    SELECTING_TEAM = "组建队伍"
    EXECUTING = "执行任务"
    COMPLETED = "已完成"

class FinalQuest:
    def __init__(self, player_count: int):
        self.required_players = self._get_required_players(player_count)
        self.status = FinalQuestStatus.NOT_STARTED
        self.nominated_leader: Optional[Player] = None
        self.team: List[Player] = []
        self.votes: Dict[Player, bool] = {}  # 投票选择领袖
        self.results: List[QuestResult] = []
        
    def _get_required_players(self, player_count: int) -> int:
        """获取最终任务需要的队员数量"""
        requirements = {
            4: 3,  # 4人游戏最终任务需要3人
            5: 3, 6: 4, 7: 4, 8: 5, 9: 5, 10: 5
        }
        return requirements[player_count]

class GameResult:
    def __init__(self):
        self.winning_team: Optional[Team] = None
        self.quest_results: List[bool] = []
        self.quest_details: List[Dict] = []  # 每个任务的详细信息
        self.mvp_player: Optional[Player] = None  # 最有价值玩家
        self.special_achievements: Dict[Player, List[str]] = {}  # 特殊成就
        
    def add_quest_detail(self, quest_number: int, leader: Player, team: List[Player], 
                        success: bool, used_magic: bool, sabotaged: bool):
        """记录任务详细信息"""
        self.quest_details.append({
            "quest_number": quest_number,
            "leader": leader.name,
            "team": [p.name for p in team],
            "success": success,
            "used_magic": used_magic,
            "sabotaged": sabotaged
        })

class TimerStatus(Enum):
    NOT_STARTED = "未开始"
    RUNNING = "进行中"
    PAUSED = "已暂停"
    EXPIRED = "已结束"

class GameTimer:
    def __init__(self, duration: int, callback: Optional[Callable] = None):
        self.duration = duration  # 持续时间（秒）
        self.start_time: Optional[datetime] = None
        self.pause_time: Optional[datetime] = None
        self.remaining_time: Optional[int] = None
        self.status = TimerStatus.NOT_STARTED
        self.callback = callback  # 时间到时的回调函数
        
    def start(self):
        """开始计时"""
        if self.status == TimerStatus.PAUSED:
            # 恢复暂停的计时器
            self.start_time = datetime.now() - timedelta(
                seconds=(self.duration - self.remaining_time)
            )
        else:
            self.start_time = datetime.now()
            self.remaining_time = self.duration
        self.status = TimerStatus.RUNNING
        
    def pause(self):
        """暂停计时"""
        if self.status == TimerStatus.RUNNING:
            self.pause_time = datetime.now()
            self.remaining_time = self.get_remaining_time()
            self.status = TimerStatus.PAUSED
            
    def reset(self):
        """重置计时器"""
        self.start_time = None
        self.pause_time = None
        self.remaining_time = self.duration
        self.status = TimerStatus.NOT_STARTED
        
    def get_remaining_time(self) -> int:
        """获取剩余时间（秒）"""
        if self.status == TimerStatus.NOT_STARTED:
            return self.duration
        elif self.status == TimerStatus.PAUSED:
            return self.remaining_time
        elif self.status == TimerStatus.EXPIRED:
            return 0
            
        elapsed = (datetime.now() - self.start_time).total_seconds()
        remaining = max(0, self.duration - int(elapsed))
        
        if remaining == 0 and self.status == TimerStatus.RUNNING:
            self.status = TimerStatus.EXPIRED
            if self.callback:
                self.callback()
                
        return remaining

class PhaseTimer:
    """阶段计时器配置"""
    LEADER_SELECTION = 60  # 领袖选择阶段 60秒
    TEAM_BUILDING = 120    # 组队阶段 120秒
    QUEST_EXECUTION = 30   # 任务执行阶段 30秒
    FINAL_LEADER_VOTE = 90 # 最终任务领袖投票 90秒
    FINAL_QUEST = 45      # 最终任务执行 45秒

class Game:
    def __init__(self, players, player_count):
        self.players = players
        self.player_count = player_count
        self.current_leader_index = 0
        self.quest_number = 1
        
        # 设置任务需求玩家数
        if self.player_count == 4:
            self.quest_requirements = [2, 3, 2, 3, 3]
        elif self.player_count == 5:
            self.quest_requirements = [2, 3, 2, 3, 3]
        elif self.player_count == 6:
            self.quest_requirements = [2, 3, 4, 3, 4]
        elif self.player_count == 7:
            self.quest_requirements = [2, 3, 3, 4, 4]
        elif self.player_count == 8:
            self.quest_requirements = [3, 4, 4, 5, 5]
        elif self.player_count == 9:
            self.quest_requirements = [3, 4, 4, 5, 5]
        elif self.player_count == 10:
            self.quest_requirements = [3, 4, 4, 5, 5]
        else:
            raise ValueError(f"不支持 {self.player_count} 人游戏")
            
        self.current_quest = Quest(self.quest_number, self.quest_requirements[0])
        self.quest_results = []
        self.successful_quests = 0
        self.failed_quests = 0
        self.current_phase = GamePhase.LEADER_TURN
        self.winner = None
        
        # 设置角色
        self.setup_roles()

    def assign_roles(self):
        """已弃用，使用setup_roles代替"""
        raise DeprecationWarning("此方法已弃用，请使用setup_roles代替")

    def setup_roles(self):
        """设置玩家角色"""
        print("[DEBUG] Setting up roles...")
        # 根据玩家数量确定角色配置
        role_config = {
            4: [Role.LOYAL_SERVANT, Role.LOYAL_SERVANT, 
                Role.MORGAN, Role.PRINCE],
            5: [Role.LOYAL_SERVANT, Role.LOYAL_SERVANT, Role.LOYAL_SERVANT, 
                Role.MORGAN, Role.PRINCE],
            6: [Role.LOYAL_SERVANT, Role.LOYAL_SERVANT, Role.LOYAL_SERVANT, 
                Role.MORGAN, Role.SHAPESHIFTER, Role.MORDRED_MINION],
            7: [Role.LOYAL_SERVANT, Role.LOYAL_SERVANT, Role.LOYAL_SERVANT, Role.DUKE,
                Role.MORGAN, Role.SHAPESHIFTER, Role.MORDRED_MINION],
            8: [Role.LOYAL_SERVANT, Role.LOYAL_SERVANT, Role.LOYAL_SERVANT, Role.LOYAL_SERVANT, Role.DUKE,
                Role.MORGAN, Role.SHAPESHIFTER, Role.MORDRED_MINION],
            9: [Role.LOYAL_SERVANT, Role.LOYAL_SERVANT, Role.LOYAL_SERVANT, Role.LOYAL_SERVANT, Role.DUKE, Role.GRAND_DUKE,
                Role.MORGAN, Role.SHAPESHIFTER, Role.MORDRED_MINION],
            10: [Role.LOYAL_SERVANT, Role.LOYAL_SERVANT, Role.LOYAL_SERVANT, Role.LOYAL_SERVANT, Role.DUKE, Role.GRAND_DUKE,
                 Role.MORGAN, Role.SHAPESHIFTER, Role.MORDRED_MINION, Role.MORDRED_MINION]
        }

        # 随机打乱角色
        roles = role_config[self.player_count].copy()
        random.shuffle(roles)
        
        # 分配角色给玩家
        for player, role in zip(self.players, roles):
            player.role = role
            player.team = role.team
            print(f"[DEBUG] Player {player.name} got role: {role.display_name} ({role.team.display_name})")

    def get_current_leader(self):
        """获取当前队长"""
        return self.players[self.current_leader_index]

    def prepare_next_quest(self):
        """准备下一轮任务"""
        self.quest_number += 1
        self.current_quest = Quest(self.quest_number, self.quest_requirements[self.quest_number - 1])
        self.current_leader_index = (self.current_leader_index + 1) % len(self.players)
        self.current_phase = GamePhase.LEADER_TURN

    def prepare_next_quest_without_leader_change(self):
        """准备下一轮任务但不自动更换队长"""
        self.quest_number += 1
        self.current_quest = Quest(self.quest_number, self.quest_requirements[self.quest_number - 1])
        # 不改变当前队长，等待手动选择
        self.current_phase = GamePhase.SELECT_NEXT_LEADER

    def add_player(self, player: Player):
        """添加玩家"""
        if not player.name.strip():
            raise ValueError("玩家名称不能为空")
            
        if len(self.players) >= self.player_count:
            raise ValueError("游戏人数已满")
            
        # 检查重复名字
        if any(p.name == player.name for p in self.players):
            raise ValueError(f"玩家名称 '{player.name}' 已存在")
            
        self.players.append(player)

    def start_game(self):
        """开始游戏"""
        print(f"[DEBUG] Starting game with {len(self.players)} players")
        if len(self.players) != self.player_count:
            raise ValueError(f"玩家数量不足 (当前 {len(self.players)}/{self.player_count})")
            
        if self.current_phase != GamePhase.SETUP:
            raise ValueError("游戏已经开始")
            
        # 设置角色
        self.setup_roles()
        
        # 开始第一个任务
        print("[DEBUG] Setting up first quest")
        self.current_phase = GamePhase.LEADER_TURN
        self.quest_number = 1
        self.current_quest = Quest(self.quest_number, self.quest_requirements[self.quest_number])
        print(f"[DEBUG] Game started, current phase: {self.current_phase.value}")

    def get_current_quest_size(self) -> int:
        """获取当前任务需要的队员数量"""
        return self.quest_requirements[len(self.quest_results) + 1]

    def next_leader(self):
        """轮换到下一位领袖"""
        self.current_leader_index = (self.current_leader_index + 1) % len(self.players)

    def is_game_over(self) -> bool:
        """检查游戏是否结束"""
        return self.current_phase == GamePhase.GAME_OVER

    def get_winning_team(self) -> Optional[Team]:
        """获取获胜阵营"""
        if not self.is_game_over():
            return None
        successes = sum(1 for result in self.quest_results if result)
        return Team.GOOD if successes >= 3 else Team.EVIL 

    def start_new_quest(self):
        """开始新的任务"""
        if self.current_quest and not self.current_quest.is_completed:
            raise ValueError("当前任务尚未完成")
            
        self.quest_number += 1
        required_players = self.quest_requirements[self.quest_number]
        self.current_quest = Quest(self.quest_number, required_players)
        self.current_phase = GamePhase.LEADER_TURN

    def assign_quest_member(self, leader: Player, member: Player):
        """领袖指派任务队员"""
        if self.current_phase != GamePhase.LEADER_TURN:
            raise ValueError("现在不是指派队员的阶段")
        if leader != self.get_current_leader():
            raise ValueError("只有当前领袖可以指派队员")
        if not self.current_quest:
            raise ValueError("没有正在进行的任务")
        
        self.current_quest.add_team_member(member)
        
        # 如果队伍已满，进入任务阶段
        if self.current_quest.is_team_full():
            self.current_phase = GamePhase.QUEST_VOTE

    def submit_quest_result(self, player: Player, success: bool, use_magic: bool = False):
        """提交任务结果"""
        if self.current_phase != GamePhase.QUEST_VOTE:
            raise ValueError("现在不是执行任务的阶段")
            
        if not self.current_quest or player not in self.current_quest.team:
            raise ValueError("该玩家不是任务队员")
            
        if any(r.player == player for r in self.current_quest.results):
            raise ValueError("该玩家已经提交过结果")
            
        # 如果使用魔法指示物，检查并消耗
        if use_magic and not player.use_magic_token():
            raise ValueError("没有可用的魔法指示物")

        self.current_quest.submit_result(player, success, use_magic)
        
        # 检查是否所有队员都提交了结果
        if len(self.current_quest.results) == self.current_quest.required_players:
            self._complete_current_quest()

    def _complete_current_quest(self):
        """完成当前任务并处理结果"""
        if not self.current_quest:
            return
        
        self.current_quest.is_completed = True
        quest_result = self.current_quest.get_final_result()
        self.quest_results.append(quest_result)
        
        # 更新任务成功/失败计数
        if quest_result:
            self.successful_quests += 1
        else:
            self.failed_quests += 1

        # 检查游戏是否结束
        if self.successful_quests >= 3:
            self._end_game(Team.GOOD)
        elif self.failed_quests >= 3:
            self._end_game(Team.EVIL)
        else:
            # 准备下一个任务
            self.next_leader()
            self.start_new_quest()

    def get_quest_status(self) -> str:
        """获取当前任务状态"""
        if not self.current_quest:
            return "没有正在进行的任务"
        
        status = f"第{self.quest_number}个任务\n"
        status += f"需要{self.current_quest.required_players}名队员\n"
        status += f"当前队员：{', '.join(p.name for p in self.current_quest.team)}\n"
        status += f"已提交结果：{len(self.current_quest.results)}/{self.current_quest.required_players}"
        return status

    def get_game_status(self):
        """获取游戏状态"""
        status = {
            'quest_number': self.quest_number,
            'current_phase': self.current_phase.value,
            'current_leader': self.get_current_leader().name,
            'players': [{
                'name': p.name,
                'is_leader': p == self.get_current_leader(),
                'role': p.role.display_name if hasattr(p, 'role') else None,
                'team': p.role.team.value if hasattr(p, 'role') else None,
                'team_display': p.role.team.display_name if hasattr(p, 'role') else None,
                'player_number': p.player_number,
                'magic_tokens': p.magic_tokens if hasattr(p, 'magic_tokens') else 0
            } for p in self.players],
            'quest_results': self.quest_results,
            'successful_quests': self.successful_quests,
            'failed_quests': self.failed_quests,
            'current_quest': {
                'required_players': self.current_quest.required_players,
                'team': [{'name': p.name, 'player_number': p.player_number} for p in self.current_quest.team],
                'votes': list(self.current_quest.votes.keys())
            }
        }
        
        # 如果游戏结束，添加获胜者信息
        if self.current_phase == GamePhase.GAME_OVER:
            status['winner'] = 'GOOD' if self.successful_quests >= 3 else 'EVIL'
            
        return status

    def use_amulet(self, user: Player, target: Player) -> AmuletResult:
        """使用护身符查验玩家阵营"""
        if not user.use_amulet():
            raise ValueError("该玩家没有可用的护身符")
            
        # 检查目标玩家是否是幻形妖
        is_shapeshifter = target.role.display_name == "摩根勒菲"
        
        # 幻形妖可以选择显示为正义阵营
        revealed_team = target.team
        is_true_team = True
        
        if is_shapeshifter:
            # 幻形妖可以选择显示为正义阵营
            revealed_team = Team.GOOD
            is_true_team = False
        
        result = AmuletResult(
            target_player=target,
            revealed_team=revealed_team,
            is_true_team=is_true_team
        )
        
        # 记录护身符使用历史
        amulet_use = AmuletUse(user, target)
        amulet_use.result = result
        amulet_use.timestamp = self.get_current_quest_number()
        self.amulet_history.append(amulet_use)
        
        return result

    def get_amulet_history(self, player: Player) -> List[AmuletUse]:
        """获取指定玩家的护身符使用历史"""
        return [use for use in self.amulet_history 
                if use.user == player or use.target == player]

    def get_current_quest_number(self) -> int:
        """获取当前任务编号"""
        return len(self.quest_results) + 1

    def get_amulet_status(self, player: Player) -> str:
        """获取玩家的护身符状态"""
        history = self.get_amulet_history(player)
        status = f"护身符剩余：{player.amulets}个\n"
        
        if history:
            status += "使用记录：\n"
            for use in history:
                if use.user == player:
                    status += (f"第{use.timestamp}轮 查验了 {use.target.name} "
                             f"显示为 {use.result.revealed_team.value}阵营\n")
                elif use.target == player:
                    status += f"第{use.timestamp}轮 被 {use.user.name} 查验\n"
        
        return status 

    def use_special_ability(self, user: Player, target: Optional[Player] = None) -> str:
        """使用特殊能力"""
        if not user.role or not user.role.can_use_ability():
            raise ValueError("无法使用特殊能力")

        ability = user.role.special_ability
        result_message = ""

        if ability == SpecialAbility.SEE_EVIL:
            result_message = self._use_see_evil(user)
        elif ability == SpecialAbility.PREDICT_QUEST:
            result_message = self._use_predict_quest(user)
        elif ability == SpecialAbility.PROTECT_PLAYER:
            if not target:
                raise ValueError("需要指定目标玩家")
            result_message = self._use_protect_player(user, target)
        elif ability == SpecialAbility.STEAL_MAGIC:
            if not target:
                raise ValueError("需要指定目标玩家")
            result_message = self._use_steal_magic(user, target)
        elif ability == SpecialAbility.SABOTAGE_QUEST:
            result_message = self._use_sabotage_quest(user)
        elif ability == SpecialAbility.KNOW_EVIL_TEAM:
            result_message = self._use_know_evil_team(user)

        # 记录能力使用
        self.ability_history.append(AbilityUse(user, ability, target))
        user.role.ability_used = True
        
        return result_message

    def _use_see_evil(self, user: Player) -> str:
        """圣骑士能力：看到邪恶玩家"""
        evil_players = [p.name for p in self.players if p.team == Team.EVIL]
        return f"邪恶阵营的玩家有：{', '.join(evil_players)}"

    def _use_predict_quest(self, user: Player) -> str:
        """预言家能力：预知任务结果"""
        if not self.current_quest:
            raise ValueError("当前没有进行中的任务")
        
        # 预测当前任务的结果（基于当前队伍的邪恶玩家数量）
        evil_count = sum(1 for p in self.current_quest.team if p.team == Team.EVIL)
        prediction = evil_count == 0
        self.quest_predictions[self.quest_number] = prediction
        
        return f"预言家预测此次任务将{'成功' if prediction else '失败'}"

    def _use_protect_player(self, user: Player, target: Player) -> str:
        """守护者能力：保护玩家免受干扰"""
        if target not in self.current_quest.team:
            raise ValueError("只能保护当前任务的队员")
        
        self.protected_players.add(target)
        return f"守护者保护了 {target.name}"

    def _use_steal_magic(self, user: Player, target: Player) -> str:
        """黑暗法师能力：窃取魔法指示物"""
        if target.magic_tokens <= 0:
            raise ValueError("目标玩家没有魔法指示物")
        
        target.magic_tokens -= 1
        user.magic_tokens += 1
        return f"从 {target.name} 处窃取了一个魔法指示物"

    def _use_sabotage_quest(self, user: Player) -> str:
        """暗影刺客能力：干扰任务结果"""
        if not self.current_quest:
            raise ValueError("当前没有进行中的任务")
        
        # 标记任务被干扰
        self.current_quest.is_sabotaged = True
        return "任务已被干扰"

    def _use_know_evil_team(self, user: Player) -> str:
        """摩根勒菲能力：知晓邪恶阵营"""
        evil_players = [(p.name, p.role.display_name) for p in self.players if p.team == Team.EVIL]
        return f"邪恶阵营成员：" + ", ".join([f"{name}({role})" for name, role in evil_players])

    def get_ability_history(self, player: Player) -> List[str]:
        """获取能力使用历史"""
        history = []
        for use in self.ability_history:
            if use.user == player:
                target_info = f" -> {use.target.name}" if use.target else ""
                history.append(f"使用了 {use.ability.name}{target_info}")
            elif use.target == player:
                history.append(f"被 {use.user.name} 使用了 {use.ability.name}")
        return history 

    def start_final_quest(self):
        """开始最终任务阶段"""
        if self.current_phase != GamePhase.FINAL_QUEST:
            raise ValueError("现在不是最终任务阶段")
        
        self.final_quest = FinalQuest(self.player_count)
        self.final_quest.status = FinalQuestStatus.SELECTING_LEADER
        self._setup_phase_timer(PhaseTimer.FINAL_LEADER_VOTE)
        
    def nominate_final_leader(self, nominator: Player, nominee: Player):
        """提名最终任务的领袖"""
        if not self.final_quest or self.final_quest.status != FinalQuestStatus.SELECTING_LEADER:
            raise ValueError("现在不是选择领袖的阶段")
        
        if self.final_quest.nominated_leader:
            raise ValueError("已经有被提名的领袖")
            
        # 只有正义阵营可以提名领袖
        if nominator.team != Team.GOOD:
            raise ValueError("只有正义阵营可以提名领袖")
            
        self.final_quest.nominated_leader = nominee
        
    def vote_for_final_leader(self, voter: Player, approve: bool):
        """为最终任务领袖投票"""
        if not self.final_quest or not self.final_quest.nominated_leader:
            raise ValueError("没有可以投票的领袖提名")
            
        if voter in self.final_quest.votes:
            raise ValueError("你已经投过票了")
            
        self.final_quest.votes[voter] = approve
        
        # 检查是否所有人都投票了
        if len(self.final_quest.votes) == self.player_count:
            self._resolve_final_leader_vote()
            
    def _resolve_final_leader_vote(self):
        """处理最终任务领袖的投票结果"""
        if not self.final_quest:
            return
            
        approve_count = sum(1 for vote in self.final_quest.votes.values() if vote)
        
        # 需要过半数同意
        if approve_count > self.player_count / 2:
            self.final_quest.status = FinalQuestStatus.SELECTING_TEAM
        else:
            # 投票失败，重置提名
            self.final_quest.nominated_leader = None
            self.final_quest.votes.clear()
            
    def assign_final_quest_member(self, leader: Player, member: Player):
        """最终任务领袖指派队员"""
        if not self.final_quest or self.final_quest.status != FinalQuestStatus.SELECTING_TEAM:
            raise ValueError("现在不是指派队员的阶段")
            
        if leader != self.final_quest.nominated_leader:
            raise ValueError("只有被选中的领袖可以指派队员")
            
        if len(self.final_quest.team) >= self.final_quest.required_players:
            raise ValueError("队伍已满")
            
        if member in self.final_quest.team:
            raise ValueError("该玩家已经在队伍中")
            
        self.final_quest.team.append(member)
        
        # 检查队伍是否已满
        if len(self.final_quest.team) == self.final_quest.required_players:
            self.final_quest.status = FinalQuestStatus.EXECUTING
            
    def submit_final_quest_result(self, player: Player, success: bool, use_magic: bool = False):
        """提交最终任务结果"""
        if not self.final_quest or self.final_quest.status != FinalQuestStatus.EXECUTING:
            raise ValueError("现在不是执行任务的阶段")
            
        if player not in self.final_quest.team:
            raise ValueError("只有任务队员才能提交结果")
            
        if any(r.player == player for r in self.final_quest.results):
            raise ValueError("你已经提交过结果了")
            
        # 处理魔法指示物
        if use_magic and not player.use_magic_token():
            raise ValueError("没有可用的魔法指示物")
            
        self.final_quest.results.append(QuestResult(success, player, use_magic))
        
        # 检查是否所有人都提交了结果
        if len(self.final_quest.results) == self.final_quest.required_players:
            self._complete_final_quest()
            
    def _complete_final_quest(self):
        """完成最终任务并处理结果"""
        if not self.final_quest:
            return
            
        self.final_quest.status = FinalQuestStatus.COMPLETED
        
        # 计算最终结果
        # 如果有人使用了魔法指示物，任务必定成功
        if any(result.used_magic for result in self.final_quest.results):
            final_result = True
        else:
            # 最终任务中只要有一个失败就算失败
            final_result = all(result.success for result in self.final_quest.results)
            
        self.quest_results.append(final_result)
        self.current_phase = GamePhase.GAME_OVER
        
    def get_final_quest_status(self) -> str:
        """获取最终任务状态"""
        if not self.final_quest:
            return "最终任务尚未开始"
            
        status = f"最终任务状态：{self.final_quest.status.value}\n"
        
        if self.final_quest.nominated_leader:
            status += f"提名的领袖：{self.final_quest.nominated_leader.name}\n"
            status += f"投票情况：{len(self.final_quest.votes)}/{self.player_count}\n"
            
        if self.final_quest.team:
            status += f"当前队员：{', '.join(p.name for p in self.final_quest.team)}\n"
            status += f"已提交结果：{len(self.final_quest.results)}/{self.final_quest.required_players}\n"
            
        return status

    def _end_game(self, winning_team: Team):
        """结束游戏"""
        self.current_phase = GamePhase.GAME_OVER
        self.game_result = {
            'winning_team': winning_team,
            'quest_results': self.quest_results,
            'total_quests': len(self.quest_results)
        }

    def get_game_summary(self) -> str:
        """获取游戏总结"""
        if not self.game_result:
            return "游戏尚未结束"
        
        summary = [
            f"\n游戏结束！{self.game_result['winning_team'].value}阵营胜利！",
            f"\n任务结果统计:",
            f"总任务数: {self.game_result['total_quests']}",
            f"成功任务: {self.successful_quests}",
            f"失败任务: {self.failed_quests}",
            "\n各任务详细结果:"
        ]
        
        for i, result in enumerate(self.quest_results, 1):
            summary.append(f"第{i}个任务: {'成功' if result else '失败'}")
            
        return "\n".join(summary)

    def get_player_stats(self, player: Player) -> str:
        """获取玩家统计信息"""
        if not self.game_result:
            return "游戏尚未结束"
            
        stats = [
            f"\n玩家: {player.name}",
            f"角色: {player.role.display_name}",
            f"阵营: {player.team.value}",
            f"剩余魔法指示物: {player.magic_tokens}",
            f"剩余护身符: {player.amulets}"
        ]
        
        return "\n".join(stats)

    def _setup_phase_timer(self, duration: int):
        """设置阶段计时器"""
        if not self.is_timer_enabled:
            return
            
        self.current_timer = GameTimer(duration, self._handle_timer_expired)
        self.current_timer.start()
        
    def _handle_timer_expired(self):
        """处理计时器到期"""
        if self.current_phase == GamePhase.LEADER_TURN:
            self._auto_select_team()
        elif self.current_phase == GamePhase.QUEST_VOTE:
            self._auto_complete_quest()
        elif self.current_phase == GamePhase.FINAL_QUEST:
            self._handle_final_quest_timeout()
            
    def _auto_select_team(self):
        """自动选择队员（时间到时）"""
        if not self.current_quest:
            return
            
        leader = self.get_current_leader()
        required_count = self.get_current_quest_size()
        
        # 随机选择剩余需要的队员
        available_players = [p for p in self.players if p not in self.current_quest.team]
        needed_count = required_count - len(self.current_quest.team)
        
        if needed_count > 0 and available_players:
            selected = random.sample(available_players, min(needed_count, len(available_players)))
            for player in selected:
                self.assign_quest_member(leader, player)
                
    def _auto_complete_quest(self):
        """自动完成任务（时间到时）"""
        if not self.current_quest:
            return
            
        # 未提交结果的队员自动提交
        for player in self.current_quest.team:
            if not any(r.player == player for r in self.current_quest.results):
                # 邪恶阵营自动选择失败，正义阵营自动选择成功
                success = player.team == Team.GOOD
                self.submit_quest_result(player, success)
                
    def _handle_final_quest_timeout(self):
        """处理最终任务超时"""
        if not self.final_quest:
            return
            
        if self.final_quest.status == FinalQuestStatus.SELECTING_LEADER:
            # 自动结束领袖投票
            self._resolve_final_leader_vote()
        elif self.final_quest.status == FinalQuestStatus.SELECTING_TEAM:
            # 自动完成队伍选择
            self._auto_select_final_team()
        elif self.final_quest.status == FinalQuestStatus.EXECUTING:
            # 自动完成任务执行
            self._auto_complete_final_quest()
            
    def get_timer_status(self) -> str:
        """获取计时器状态"""
        if not self.current_timer or not self.is_timer_enabled:
            return "计时器未启用"
            
        remaining = self.current_timer.get_remaining_time()
        return f"剩余时间：{remaining}秒"
        
    def pause_timer(self):
        """暂停计时器"""
        if self.current_timer:
            self.current_timer.pause()
            
    def resume_timer(self):
        """恢复计时器"""
        if self.current_timer:
            self.current_timer.start()
            
    def toggle_timer(self):
        """开关计时器"""
        self.is_timer_enabled = not self.is_timer_enabled
        if not self.is_timer_enabled and self.current_timer:
            self.current_timer.pause()

    def get_player_info(self, player_name: str):
        """获取指定玩家的信息（包括他能看到的其他玩家信息）"""
        player = next((p for p in self.players if p.name == player_name), None)
        if not player:
            print(f"[DEBUG] Player {player_name} not found in game")
            return None

        print(f"[DEBUG] Getting info for {player_name}, role: {player.role.display_name if player.role else 'None'}")
        
        visible_info = []
        for i, other in enumerate(self.players):
            info = {
                'name': other.name,
                'number': i + 1,
                'is_leader': other == self.get_current_leader(),
                'is_self': other == player
            }

            # 如果是自己，显示完整信息
            if other == player:
                info.update({
                    'role': other.role.display_name,
                    'role_description': other.role.description,
                    'team': other.team.value,
                    'team_display': other.team.display_name
                })
                print(f"[DEBUG] Self info for {player_name}: {info}")
            
            # 根据角色规则显示其他玩家信息
            elif player.role == Role.MORGAN:
                # 摩根勒菲知道所有邪恶方的身份，除了幻形妖
                if other.team == Team.EVIL and other.role != Role.SHAPESHIFTER:
                    info['team'] = Team.EVIL.value
                    info['team_display'] = Team.EVIL.display_name
                    info['role'] = other.role.display_name  # 摩根勒菲知道其他邪恶方的具体角色
            
            elif player.role == Role.MORDRED_MINION:
                # 莫德雷德的爪牙可以看到摩根勒菲和王储，不知道幻形妖
                if other.role == Role.MORGAN or other.role == Role.PRINCE:
                    info['team'] = Team.EVIL.value
                    info['team_display'] = Team.EVIL.display_name
                    info['role'] = other.role.display_name  # 莫德雷德爪牙知道角色
            
            elif player.role == Role.PRINCE:
                # 王储不知道谁是邪恶方
                pass

            elif player.role == Role.SHAPESHIFTER:
                # 幻形妖不知道谁是邪恶方
                pass

            visible_info.append(info)

        return visible_info 