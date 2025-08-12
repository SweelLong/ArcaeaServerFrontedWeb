from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import os
import uuid
import random
from datetime import datetime
from functools import wraps
from .event_db import DatabaseOperations

bp = Blueprint('event', __name__, url_prefix='/event', template_folder='../../templates/event')
db_ops = DatabaseOperations()
CONTRIBUTIONS_FOLDER = os.path.join(os.path.dirname(__file__), 'contributions')
os.makedirs(CONTRIBUTIONS_FOLDER, exist_ok=True)

def login_required(view):
    """登录装饰器，不影响服务器其他路由，与web路由的登录区分开"""
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash('请先登录')
            return redirect(url_for('event.login', next=request.url))
        return view(** kwargs)
    return wrapped_view

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
def index():
    """首页只需要按钮没有后端处理"""
    return render_template('event/index.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db_ops.verify_user(username, password)
        if user:
            session['user_id'] = user['user_id']
            session['username'] = user['name']
            next_page = request.args.get('next', url_for('event.index'))
            return redirect(next_page)
        else:
            flash('用户名或密码错误')
    return render_template('event/login.html')

@bp.route('/logout')
def logout():
    """登出"""
    session.clear()
    flash('已成功登出')
    return redirect(url_for('event.index'))

@bp.route('/lottery', methods=['GET', 'POST'])
@login_required
def lottery():
    """抽奖"""
    user_id = session['user_id']
    today_draw = db_ops.daily_draw(user_id)
    has_drawn = today_draw is not None
    result = None
    if has_drawn:
        result = today_draw[2]
    available_limited = db_ops.get_available_limited_prizes()
    claimed_count = db_ops.get_claimed_limited_prizes()
    user_has_banner = db_ops.get_user_banner_status(user_id)
    limited_winners = db_ops.get_limited_prize_winners()
    if request.method == 'POST' and not has_drawn:
        base_probabilities = {
            # 所有限量奖品总概率（3个）
            #"limited": 15,
            "limited": 3,
            # banner仅能获取一次（1个）
            #"banner": 50 if not user_has_banner else 0,  
            "banner": 39.7 if not user_has_banner else 0,  
            # 500虚实构想初始概率（无限量）
            "currency": 60 
        }
        # 每被领走一个限量奖品，500虚实构想概率+(5%->)1%
        currency_bonus = claimed_count * 1
        base_probabilities["currency"] += currency_bonus
        # 对应减少限量奖品总概率,因为总数不能超过100%
        base_probabilities["limited"] = max(0, base_probabilities["limited"] - currency_bonus)
        # 个人概率调整：如果已获得banner，500虚实构想概率+(50%->)37%
        #personal_bonus = 50 if user_has_banner else 0
        personal_bonus = 37 if user_has_banner else 0
        if personal_bonus > 0:
            # 从剩余概率中分配
            base_probabilities["currency"] += personal_bonus
        prize_pool = []
        # 添加限量奖品，按剩余数量平均分配limited概率
        if available_limited and base_probabilities["limited"] > 0:
            limited_per_prize = base_probabilities["limited"] / len(available_limited)
            for prize in available_limited:
                prize_pool.extend([(prize['prize_id'], prize['prize_name']) for _ in range(int(limited_per_prize * 10))])
        # 添加纪念banner
        if base_probabilities["banner"] > 0:
            prize_pool.extend([("banner", "《星辰》纪念banner") for _ in range(int(base_probabilities["banner"] * 10))])
        # 添加500虚实构想
        prize_pool.extend([("currency", "500虚实构想") for _ in range(int(base_probabilities["currency"] * 10))])
        if prize_pool:
            selected = random.choice(prize_pool)
            prize_id, prize_name = selected
            if prize_id in ["badge", "streamer", "stub"]:
                success = db_ops.claim_limited_prize(user_id, prize_id, prize_name)
                if success:
                    result = prize_name
                    available_limited = db_ops.get_available_limited_prizes()
                    claimed_count = db_ops.get_claimed_limited_prizes()
                else:
                    result = "500虚实构想"
                    db_ops.record_lottery_result(user_id, result)
            else:
                db_ops.record_lottery_result(user_id, prize_name)
                result = prize_name
                if prize_id == "banner":
                    user_has_banner = True
        has_drawn = True
    # 前端展示用的字典
    all_prizes = [
        {"id": "badge", "name": "sense of wonder吧唧", "prob": "1%", "limited": True},
        {"id": "streamer", "name": "克丽斯腾流麻", "prob": "1%", "limited": True},
        {"id": "stub", "name": "克丽斯腾票根", "prob": "1%", "limited": True},
        {"id": "banner", "name": "《星辰》纪念banner", "prob": "37%", "limited": False},
        {"id": "currency", "name": "500虚实构想", "prob": f"60%{'+1%'*claimed_count}{'+37%' if user_has_banner else ''}", "limited": False}
    ]
    # 标记已被领取的奖品
    available_ids = [p["prize_id"] for p in available_limited]
    for prize in all_prizes:
        if prize["limited"]:
            prize["is_available"] = prize["id"] in available_ids
        else:
            prize["is_available"] = True if prize["id"] != "banner" else not user_has_banner
    
    return render_template('event/lottery.html', has_drawn=has_drawn, result=result,today=datetime.now().strftime('%Y-%m-%d'),all_prizes=all_prizes,user_has_banner=user_has_banner,limited_winners=limited_winners)

@bp.route('/contribution', methods=['GET', 'POST'])
@login_required
def contribution():
    """投稿"""
    user_id = session['user_id']
    contributions = db_ops.get_user_contributions(user_id)
    if request.method == 'POST':
        name = request.form['name']
        if 'file' not in request.files:
            flash('请选择文件')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('请选择一个文件')
            return redirect(request.url)
        if not file.filename.endswith('.zip'):
            flash('请上传zip格式的文件')
            return redirect(request.url)
        unique_filename = f"{user_id}_{name}_{uuid.uuid4().hex}.zip" # 网页版商店功能吸取的教训
        file_path = os.path.join(CONTRIBUTIONS_FOLDER, unique_filename)
        file.save(file_path)
        success = db_ops.add_contribution(user_id, name, unique_filename)
        if success:
            flash('投稿成功')
            return redirect(url_for('event.contribution'))
        else:
            flash('同名投稿已存在')
            os.remove(file_path)
    return render_template('event/contribution.html', contributions=contributions)