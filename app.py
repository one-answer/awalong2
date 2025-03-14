from flask import Flask, render_template, jsonify, request, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from avalon import AvalonGame
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
# 修改 SocketIO 的初始化配置，允许跨域访问
socketio = SocketIO(app, cors_allowed_origins="*")
games = {}  # 存储游戏实例
game_states = {}  # 存储每个游戏的状态

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('create_game')
def handle_create_game(data):
    player_count = int(data['player_count'])
    game_id = secrets.token_hex(8)
    games[game_id] = AvalonGame(player_count)
    game_states[game_id] = {
        'team_votes': {},
        'quest_votes': {},
        'connected_players': set()
    }
    emit('game_created', {'game_id': game_id})

@socketio.on('join_game')
def handle_join_game(data):
    game_id = data['game_id']
    
    if game_id not in games:
        emit('error', {'message': '游戏不存在'})
        return
        
    game = games[game_id]
    
    # 自动分配最小的可用编号
    connected_players = game_states[game_id]['connected_players']
    if len(connected_players) >= game.player_count:
        emit('error', {'message': '房间已满'})
        return
        
    for i in range(game.player_count):
        if i not in connected_players:
            player_id = i
            break
    
    join_room(game_id)
    game_states[game_id]['connected_players'].add(player_id)
    
    # 存储玩家的socket id
    if 'player_sids' not in game_states[game_id]:
        game_states[game_id]['player_sids'] = {}
    game_states[game_id]['player_sids'][player_id] = request.sid
    
    # 当所有玩家都加入后，分配角色
    if len(game_states[game_id]['connected_players']) == game.player_count:
        game.assign_roles()
        # 给所有玩家发送他们的角色信息
        for pid, sid in game_states[game_id]['player_sids'].items():
            player_name, role = game.players[pid]
            role_info = {'role': role}
            
            if role == '梅林':
                evil_players = [j for j, (_, r) in enumerate(game.players)
                            if r in ["刺客", "爪牙"]]
                role_info['evil_players'] = evil_players
            elif role in ["刺客", "爪牙"]:
                evil_players = [j for j, (_, r) in enumerate(game.players)
                            if r in ["刺客", "爪牙"]]
                role_info['evil_players'] = evil_players
            
            emit('role_info', role_info, room=sid)
    else:
        # 如果还有玩家未加入，发送等待消息
        emit('role_info', {'role': '等待其他玩家加入...'})
    
    # 广播玩家加入消息
    socketio.emit('player_joined', {
        'player_id': player_id,
        'connected_players': list(game_states[game_id]['connected_players']),
        'all_players_joined': len(game_states[game_id]['connected_players']) == game.player_count
    }, room=game_id)
    
    # 只有当所有玩家都加入后才开始游戏
    if len(game_states[game_id]['connected_players']) == game.player_count:
        emit_game_state(game_id)

@socketio.on('disconnect')
def handle_disconnect():
    # 获取当前socket的session id
    sid = request.sid
    for game_id in games:
        if game_id in game_states and 'player_sids' not in game_states[game_id]:
            game_states[game_id]['player_sids'] = {}
        
        # 找到断开连接的玩家
        player_sids = game_states[game_id]['player_sids']
        disconnected_player = None
        for player_id, player_sid in player_sids.items():
            if player_sid == sid:
                disconnected_player = player_id
                break
        
        if disconnected_player is not None:
            game_states[game_id]['connected_players'].remove(disconnected_player)
            del game_states[game_id]['player_sids'][disconnected_player]
            socketio.emit('player_left', {
                'player_id': disconnected_player + 1,  # 转换回显示用的编号
                'connected_players': [p + 1 for p in game_states[game_id]['connected_players']]
            }, room=game_id)

def emit_game_state(game_id):
    game = games[game_id]
    socketio.emit('game_state', {
        'current_quest': game.current_quest + 1,
        'quest_results': ['成功' if r else '失败' for r in game.quest_results],
        'required_players': game.get_quest_requirement(),
        'leader': game.leader_index + 1,
        'vote_track': game.vote_track,
        'player_count': game.player_count
    }, room=game_id)

@socketio.on('propose_team')
def handle_propose_team(data):
    game_id = data['game_id']
    team = [int(x) - 1 for x in data['team']]  # 转换为内部索引
    
    if game_id not in games:
        emit('error', {'message': '游戏不存在'})
        return
        
    game = games[game_id]
    if game.propose_team(game.leader_index, team):
        game_states[game_id]['team_votes'] = {}  # 重置投票状态
        socketio.emit('team_proposed', {
            'team': [x + 1 for x in team],
            'player_count': game.player_count
        }, room=game_id)
    else:
        emit('error', {'message': '无效的队伍选择'})

@socketio.on('team_vote')
def handle_team_vote(data):
    game_id = data['game_id']
    vote = data['vote']
    player_id = int(data['player_id']) - 1  # 转换为内部索引
    
    if game_id not in games:
        emit('error', {'message': '游戏不存在'})
        return
        
    game = games[game_id]
    game_states[game_id]['team_votes'][player_id] = vote
    
    # 检查是否所有玩家都已投票
    if len(game_states[game_id]['team_votes']) == game.player_count:
        votes = [game_states[game_id]['team_votes'][i] 
                for i in range(game.player_count)]
        result = game.team_vote(votes)
        socketio.emit('team_vote_result', {
            'success': result,
            'votes': {str(k): v for k, v in game_states[game_id]['team_votes'].items()},  # 转换为字符串键
            'team': [x + 1 for x in game.quest_team] if result else []  # 如果投票通过，发送队员列表
        }, room=game_id)
        game_states[game_id]['team_votes'] = {}  # 重置投票状态
        emit_game_state(game_id)

@socketio.on('quest_vote')
def handle_quest_vote(data):
    game_id = data['game_id']
    vote = data['vote']
    player_id = int(data['player_id']) - 1  # 转换为内部索引
    
    if game_id not in games:
        emit('error', {'message': '游戏不存在'})
        return
        
    game = games[game_id]
    if player_id not in game.quest_team:
        emit('error', {'message': '你不是任务队员'})
        return
        
    game_states[game_id]['quest_votes'][player_id] = vote
    
    # 检查是否所有任务队员都已投票
    if len(game_states[game_id]['quest_votes']) == len(game.quest_team):
        votes = [game_states[game_id]['quest_votes'][i] for i in game.quest_team]
        result = game.quest_vote(votes)
        game_over, message = game.check_game_state()
        
        socketio.emit('quest_vote_result', {
            'success': result,
            'vote_count': {
                'success': sum(1 for v in votes if v),
                'fail': sum(1 for v in votes if not v)
            },
            'game_over': game_over,
            'message': message
        }, room=game_id)
        
        game_states[game_id]['quest_votes'] = {}  # 重置投票状态
        emit_game_state(game_id)

@socketio.on('assassinate')
def handle_assassinate(data):
    game_id = data['game_id']
    target = int(data['target']) - 1
    
    if game_id not in games:
        emit('error', {'message': '游戏不存在'})
        return
        
    game = games[game_id]
    merlin_index = next(i for i, (_, role) in enumerate(game.players) if role == '梅林')
    success = target == merlin_index
    
    emit('assassination_result', {
        'success': success,
        'message': "刺客成功刺杀梅林！邪恶方获胜！" if success else "刺客猜错了！正义方获胜！"
    }, room=game_id)

@socketio.on('validate_game')
def handle_validate_game(data):
    game_id = data['game_id']
    if game_id in games:
        game = games[game_id]
        emit('game_validated', {
            'valid': True,
            'player_count': game.player_count,
            'connected_players': [p + 1 for p in game_states[game_id]['connected_players']]
        })
    else:
        emit('game_validated', {
            'valid': False
        })

if __name__ == '__main__':
    # 修改运行配置，允许外部访问
    socketio.run(app, debug=True, host='0.0.0.0', port=5001) 