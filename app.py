#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from game import Game, Team, GamePhase, Player, Role
import random
import string
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # 更改为一个安全的密钥
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 存储所有房间
rooms = {}

def generate_room_code():
    """生成4位数字房间代码"""
    return str(random.randint(1000, 9999))

class Player:
    def __init__(self, name):
        self.name = name
        self.is_host = False
        self.role = None
        self.team = None
        self.player_number = None  # 添加玩家编号字段
        self.magic_tokens = 0  # 添加魔法指示物字段

class Room:
    def __init__(self, host_name, player_count):
        self.code = generate_room_code()
        self.host_name = host_name
        self.player_count = player_count
        # 创建房主玩家并设置为房主
        host_player = Player(host_name)
        host_player.is_host = True
        host_player.player_number = 1  # 房主为1号玩家
        self.players = [host_player]
        self.game = None  # 初始化时不创建游戏

    def add_player(self, player_name):
        """添加玩家到房间"""
        if len(self.players) >= self.player_count:
            raise ValueError("房间已满")
        if any(p.name == player_name for p in self.players):
            raise ValueError("玩家名称已存在")
        
        new_player = Player(player_name)
        new_player.player_number = len(self.players) + 1  # 玩家编号从1开始递增
        self.players.append(new_player)

    def start_game(self):
        """开始游戏"""
        if len(self.players) != self.player_count:
            raise ValueError("玩家数量不足")
        
        # 创建游戏实例，传入玩家列表和玩家数量
        self.game = Game(self.players, self.player_count)

    def _generate_room_code(self) -> str:
        """生成房间代码"""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase, k=4))
            if code not in rooms:
                return code

    def remove_player(self, player_name: str) -> bool:
        """从房间移除玩家"""
        self.players = [p for p in self.players if p.name != player_name]
        return True

    def get_player_count(self) -> int:
        """获取当前玩家数量"""
        return len(self.players)

    def is_full(self) -> bool:
        """检查房间是否已满"""
        return self.get_player_count() >= self.player_count

    def to_dict(self) -> dict:
        """转换房间信息为字典"""
        return {
            'code': self.code,
            'host_name': self.host_name,
            'player_count': self.player_count,
            'players': [{
                'name': p.name,
                'is_host': p.is_host,
                'player_number': p.player_number
            } for p in self.players],
            'game_started': self.game is not None
        }

@app.route('/')
def index():
    """主页路由"""
    return render_template('index.html')

@app.route('/game')
def game():
    """游戏页面路由"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """健康检查路由"""
    return {'status': 'ok'}

@app.errorhandler(403)
def forbidden_error(error):
    """处理403错误"""
    return render_template('error.html', error="403 Forbidden - 您未获授权访问此页面"), 403

@app.errorhandler(404)
def not_found_error(error):
    """处理404错误"""
    return render_template('error.html', error="404 Not Found - 页面不存在"), 404

@app.errorhandler(500)
def internal_error(error):
    """处理500错误"""
    return render_template('error.html', error="500 Internal Server Error - 服务器内部错误"), 500

@socketio.on('connect')
def handle_connect():
    """处理客户端连接"""
    print(f"[DEBUG] Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接"""
    print(f"[DEBUG] Client disconnected: {request.sid}")

@socketio.on('create_room')
def handle_create_room(data):
    """处理创建房间请求"""
    try:
        print(f"[DEBUG] Received create_room request: {data}")
        player_count = data.get('player_count', 5)
        
        # 自动生成房主名称为"玩家1"
        host_name = "玩家1"

        room = Room(host_name, player_count)
        rooms[room.code] = room

        # 加入房间的Socket.IO房间
        join_room(room.code)
        join_room(f"{room.code}_{host_name}")
        
        print(f"[DEBUG] Room created: {room.code}")
        print(f"[DEBUG] Host: {host_name}")

        room_info = room.to_dict()
        # 广播房间创建消息
        socketio.emit('room_update', room_info, to=room.code)
        
        return {'room_info': room_info, 'player_name': host_name}
    except Exception as e:
        print(f"[ERROR] Exception in create_room: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

@socketio.on('join_room')
def handle_join_room(data):
    """处理加入房间请求"""
    try:
        print(f"[DEBUG] Received join_room request: {data}")
        room_code = data.get('room_code', '').strip().upper()

        if not room_code:
            return {'error': '请输入房间代码'}

        room = rooms.get(room_code)
        if not room:
            return {'error': '房间不存在'}
            
        # 自动生成玩家名称，基于现有玩家数量
        next_player_number = len(room.players) + 1
        player_name = f"玩家{next_player_number}"

        # 添加玩家到房间
        room.add_player(player_name)
        
        # 将玩家加入房间的Socket.IO房间
        join_room(room_code)
        join_room(f"{room_code}_{player_name}")
        
        print(f"[DEBUG] Player {player_name} joined room {room_code}")
        print(f"[DEBUG] Current players: {[p.name for p in room.players]}")

        # 广播房间更新给所有玩家
        room_info = room.to_dict()
        socketio.emit('room_update', room_info, to=room_code)
        print(f"[DEBUG] Broadcasted room update to all players")

        return {'room_info': room_info, 'player_name': player_name}
    except Exception as e:
        print(f"[ERROR] Exception in join_room: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

@socketio.on('leave_room')
def handle_leave_room(data):
    """离开房间"""
    try:
        room_code = data.get('room_code')
        player_name = data.get('player_name')

        room = rooms.get(room_code)
        if room:
            room.remove_player(player_name)
            leave_room(room_code)
            
            if not room.players:
                del rooms[room_code]
            else:
                # 广播房间更新
                emit('room_update', room.to_dict(), room=room_code)
        
        return {'success': True}
    except Exception as e:
        return {'error': str(e)}

@socketio.on('start_game')
def handle_start_game(data):
    """处理游戏开始"""
    try:
        room_code = data.get('room_code')
        player_name = data.get('player_name')

        print(f"[DEBUG] Starting game for room {room_code}, initiated by {player_name}")

        room = rooms.get(room_code)
        if not room:
            return {'error': '房间不存在'}

        if player_name != room.host_name:
            return {'error': '只有房主可以开始游戏'}

        room.start_game()
        
        # 先发送游戏开始状态
        game_state = room.game.get_game_status()
        socketio.emit('game_started', {'game_state': game_state}, to=room_code)
        print(f"[DEBUG] Game started state sent to room {room_code}")

        # 为每个玩家发送私人信息
        for player in room.game.players:
            player_info = room.game.get_player_info(player.name)
            if player_info:
                private_room = f"{room_code}_{player.name}"
                print(f"[DEBUG] Sending private info to {player.name} in room {private_room}")
                # 直接使用 emit 而不是 socketio.emit
                emit('player_info', {
                    'player_info': player_info
                }, to=private_room)
                print(f"[DEBUG] Info sent to {player.name} in {private_room}")
        
        return {'success': True}
    except Exception as e:
        print(f"[ERROR] Exception in start_game: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

@socketio.on('select_team')
def handle_select_team(data):
    """处理领袖选择队员"""
    try:
        room_code = data.get('room_code')
        player_name = data.get('player_name')
        selected_team = data.get('selected_team', [])

        room = rooms.get(room_code)
        if not room:
            return {'error': '房间不存在'}

        game = room.game
        if game.current_phase != GamePhase.LEADER_TURN:
            return {'error': '当前不是选择队员阶段'}

        if player_name != game.get_current_leader().name:
            return {'error': '只有领袖可以选择队员'}

        # 验证选择的队员数量
        required_players = game.quest_requirements[game.quest_number]
        if len(selected_team) != required_players:
            return {'error': f'必须选择 {required_players} 名队员'}

        # 设置任务队员
        selected_players = [p for p in game.players if p.name in selected_team]
        game.current_quest.team = selected_players
        game.current_phase = GamePhase.TEAM_VOTE

        # 广播游戏状态更新
        emit('game_update', {
            'game_state': game.get_game_status()
        }, room=room_code)

        return {'success': True}
    except Exception as e:
        return {'error': str(e)}

@socketio.on('submit_team')
def handle_submit_team(data):
    """处理队长提交队伍"""
    try:
        room_code = data.get('room_code')
        team = data.get('team', [])
        magic_token_target = data.get('magic_token_target')  # 获取魔法指示物目标
        
        print(f"[DEBUG] Received team submission for room {room_code}:")
        print(f"Team: {team}")
        if magic_token_target:
            print(f"Magic token target: {magic_token_target}")

        room = rooms.get(room_code)
        if not room or not room.game:
            return {'error': '房间不存在或游戏未开始'}

        # 验证队伍
        if len(team) != room.game.current_quest.required_players:
            return {'error': f'队伍人数不正确，需要 {room.game.current_quest.required_players} 人'}

        # 设置任务队伍
        room.game.current_quest.team = [p for p in room.game.players if p.name in team]
        
        # 处理魔法指示物分配
        if magic_token_target:
            # 获取队长
            leader = room.game.get_current_leader()
            # 获取目标队员
            target_player = next((p for p in room.game.players if p.name == magic_token_target), None)
            
            if target_player and target_player in room.game.current_quest.team:
                # 给目标队员添加魔法指示物
                target_player.magic_tokens += 1
                print(f"[DEBUG] Assigned magic token to {target_player.name}")
            else:
                print(f"[DEBUG] Target player not found or not in team: {magic_token_target}")
        
        # 更新游戏阶段为投票阶段
        room.game.current_phase = GamePhase.QUEST_VOTE
        
        # 广播游戏状态更新
        game_state = room.game.get_game_status()
        socketio.emit('game_update', {'game_state': game_state}, to=room_code)
        
        print(f"[DEBUG] Game state updated: {game_state}")
        print(f"[DEBUG] Current phase: {room.game.current_phase}")
        print(f"[DEBUG] Quest team: {[p.name for p in room.game.current_quest.team]}")
        
        return {'success': True}
    except Exception as e:
        print(f"[ERROR] Exception in submit_team: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

@socketio.on('submit_quest_vote')
def handle_quest_vote(data):
    """处理任务投票"""
    try:
        room_code = data.get('room_code')
        success = data.get('success')
        player_name = data.get('player_name')
        
        print(f"[DEBUG] Received quest vote for room {room_code}:")
        print(f"Player: {player_name}, Vote: {'success' if success else 'fail'}")

        room = rooms.get(room_code)
        if not room or not room.game:
            return {'error': '房间不存在或游戏未开始'}

        # 获取当前玩家
        current_player = next((p for p in room.game.players if p.name == player_name), None)
        if not current_player:
            print(f"[DEBUG] Players in game: {[p.name for p in room.game.players]}")
            print(f"[DEBUG] Looking for player: {player_name}")
            return {'error': '玩家不存在'}

        # 验证玩家是否在任务队伍中
        if current_player not in room.game.current_quest.team:
            return {'error': '你不是任务队员'}

        # 检查玩家是否已经投票
        if current_player.name in room.game.current_quest.votes:
            return {'error': '你已经投过票了'}

        # 检查玩家是否有魔法指示物，如果有则必须使用
        if current_player.magic_tokens > 0:
            # 使用魔法指示物
            current_player.magic_tokens -= 1
            print(f"[DEBUG] {player_name} used a magic token (forced)")
            
            # 如果是摩根勒菲，可以选择失败，否则必须成功
            if current_player.role == Role.MORGAN:
                # 允许摩根勒菲选择任意结果
                print(f"[DEBUG] Morgan used magic token but can choose any result")
            else:
                # 非摩根勒菲使用魔法指示物时必须成功
                success = True
                print(f"[DEBUG] Non-Morgan player used magic token, forcing success")

        # 记录投票
        room.game.current_quest.votes[current_player.name] = success
        
        print(f"[DEBUG] Vote recorded for {current_player.name}: {success}")
        print(f"[DEBUG] Current votes: {room.game.current_quest.votes}")
        print(f"[DEBUG] Team size: {len(room.game.current_quest.team)}")
        print(f"[DEBUG] Votes count: {len(room.game.current_quest.votes)}")

        # 返回玩家的投票结果
        vote_result = {
            'success': True,
            'vote': success
        }

        # 检查是否所有队员都已投票
        if len(room.game.current_quest.votes) == len(room.game.current_quest.team):
            print("[DEBUG] All votes received, calculating result")
            # 计算任务结果
            fail_votes = sum(1 for vote in room.game.current_quest.votes.values() if not vote)
            quest_success = fail_votes == 0  # 任何失败票都导致任务失败
            
            print(f"[DEBUG] Quest result: {'Success' if quest_success else 'Fail'}")
            print(f"[DEBUG] Fail votes: {fail_votes}")
            
            # 记录任务结果
            room.game.quest_results.append(quest_success)
            if quest_success:
                room.game.successful_quests += 1
            else:
                room.game.failed_quests += 1

            # 检查游戏是否结束
            game_over = False
            winner = None
            if room.game.successful_quests >= 3:
                game_over = True
                winner = 'GOOD'
            elif room.game.failed_quests >= 3:
                game_over = True
                winner = 'EVIL'

            if game_over:
                room.game.current_phase = GamePhase.GAME_OVER
                room.game.winner = winner
                # 获取包含游戏结果的游戏状态
                game_state = room.game.get_game_status()
                # 广播游戏结束
                socketio.emit('game_over', {
                    'winner': game_state['winner'],
                    'game_state': game_state
                }, to=room_code)
            else:
                # 更新游戏阶段为选择下一任队长
                room.game.current_phase = GamePhase.SELECT_NEXT_LEADER
                # 准备下一轮任务，但不自动更换队长
                room.game.prepare_next_quest_without_leader_change()
                
                # 广播任务结果
                game_state = room.game.get_game_status()
                socketio.emit('quest_result', {
                    'success': quest_success,
                    'fail_count': fail_votes,
                    'game_state': game_state
                }, to=room_code)
            
            print(f"[DEBUG] Game state updated: {room.game.current_phase}")
        else:
            # 广播投票进度
            game_state = room.game.get_game_status()
            socketio.emit('game_update', {'game_state': game_state}, to=room_code)

        return vote_result
    except Exception as e:
        print(f"[ERROR] Exception in quest_vote: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

@socketio.on('select_next_leader')
def handle_select_next_leader(data):
    """处理选择下一任队长"""
    try:
        room_code = data.get('room_code')
        next_leader = data.get('next_leader')
        player_name = data.get('player_name')
        
        print(f"[DEBUG] Selecting next leader in room {room_code}:")
        print(f"Next leader: {next_leader}")
        print(f"Current player: {player_name}")

        room = rooms.get(room_code)
        if not room or not room.game:
            return {'error': '房间不存在或游戏未开始'}

        # 验证当前玩家是否是队长
        current_leader = room.game.get_current_leader()
        if player_name != current_leader.name:
            return {'error': '只有当前队长可以选择下一任队长'}

        # 验证被选择的玩家是否存在
        next_leader_player = next((p for p in room.game.players if p.name == next_leader), None)
        if not next_leader_player:
            return {'error': '选择的玩家不存在'}

        # 更新队长
        room.game.current_leader_index = room.game.players.index(next_leader_player)
        room.game.current_phase = GamePhase.LEADER_TURN

        # 广播游戏状态更新
        game_state = room.game.get_game_status()
        socketio.emit('game_update', {
            'game_state': game_state,
            'next_leader': next_leader
        }, to=room_code)
        
        print(f"[DEBUG] Next leader selected: {next_leader}")
        print(f"[DEBUG] New game phase: {room.game.current_phase}")

        return {'success': True}
    except Exception as e:
        print(f"[ERROR] Exception in select_next_leader: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

# 添加测试路由
@app.route('/test/create_room')
def test_create_room():
    """测试创建房间"""
    try:
        # 创建一个测试房间
        host_name = "测试房主"
        player_count = 5
        room = Room(host_name, player_count)
        room_code = room.code
        rooms[room_code] = room

        # 添加一些测试玩家
        test_players = ["测试玩家2", "测试玩家3", "测试玩家4", "测试玩家5"]
        for player_name in test_players:
            room.add_player(player_name)

        return {
            'success': True,
            'message': '测试房间创建成功',
            'room_info': {
                'code': room_code,
                'host_name': host_name,
                'player_count': player_count,
                'current_players': len(room.players),
                'players': [p.name for p in room.players]
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/test/list_rooms')
def test_list_rooms():
    """列出所有房间"""
    try:
        rooms_info = {}
        for code, room in rooms.items():
            rooms_info[code] = {
                'host_name': room.host_name,
                'player_count': room.player_count,
                'current_players': len(room.players),
                'players': [p.name for p in room.players],
                'game_started': room.game is not None
            }
        return {
            'success': True,
            'rooms': rooms_info
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/test/start_game/<room_code>')
def test_start_game(room_code):
    """测试开始指定房间的游戏"""
    try:
        room = rooms.get(room_code.upper())
        if not room:
            return {
                'success': False,
                'error': '房间不存在'
            }

        room.start_game()
        
        # 获取游戏状态
        game_state = room.game.get_game_status()
        
        # 获取每个玩家的角色信息
        players_info = {}
        for player in room.game.players:
            player_info = room.game.get_player_info(player.name)
            players_info[player.name] = {
                'role': player.role.display_name,
                'team': player.team.display_name,
                'visible_info': player_info
            }

        return {
            'success': True,
            'message': '游戏开始成功',
            'game_state': game_state,
            'players_info': players_info
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/test/room_info/<room_code>')
def test_room_info(room_code):
    """获取指定房间的信息"""
    try:
        room = rooms.get(room_code.upper())
        if not room:
            return {
                'success': False,
                'error': '房间不存在'
            }

        return {
            'success': True,
            'room_info': {
                'code': room.code,
                'host_name': room.host_name,
                'player_count': room.player_count,
                'current_players': len(room.players),
                'players': [p.name for p in room.players],
                'game_started': room.game is not None
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == '__main__':
    socketio.run(app, 
                 host='0.0.0.0',  # 允许外部访问
                 port=5001,       # 指定端口
                 debug=True,      # 开启调试模式
                 allow_unsafe_werkzeug=True) 