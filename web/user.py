from datetime import datetime
import hashlib
import os
import random
import sqlite3
import time
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for
import markdown
from core.error import DataExist, InputError
from core.sql import Connect
from core.user import UserRegister

bp = Blueprint('user', __name__, url_prefix='/user')

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
def index():
    return render_template('user/index.html')

@bp.route('/news', methods=['GET', 'POST'])
def news():
    news_folder = os.path.join(current_app.root_path, 'templates', 'user', 'news')
    news_items = []
    if os.path.exists(news_folder) and os.path.isdir(news_folder):
        for filename in os.listdir(news_folder):
            if filename.endswith('.md'):
                try:
                    name_part = os.path.splitext(filename)[0]
                    title_part, datetime_part = name_part.rsplit('_', 1)
                    datetime_str = datetime_part.replace('.', ':')
                    news_datetime = datetime.strptime(datetime_str, '%Y:%m:%d:%H:%M')
                    with open(os.path.join(news_folder, filename), 'r', encoding='utf-8') as f:
                        content = f.read()
                    content_html = markdown.markdown(content)
                    news_items.append({
                        'title': title_part,
                        'datetime': news_datetime,
                        'content': content,
                        'content_html': content_html,
                        'filename': filename
                    })
                except Exception as e:
                    current_app.logger.error(f"Error parsing {filename}: {e}")
    news_items.sort(key=lambda x: x['datetime'], reverse=True)
    return render_template('user/news.html', news_items=news_items)

@bp.route('/news/<filename>')
def news_detail(filename):
    news_folder = os.path.join(current_app.root_path, 'templates', 'user', 'news')
    file_path = os.path.join(news_folder, filename)
    try:
        name_part = os.path.splitext(filename)[0]
        title_part, datetime_part = name_part.rsplit('_', 1)
        datetime_str = datetime_part.replace('.', ':')
        news_datetime = datetime.strptime(datetime_str, '%Y:%m:%d:%H:%M')
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content_html = markdown.markdown(content)
        news_item = {
            'title': title_part,
            'datetime': news_datetime,
            'content_html': content_html,
            'filename': filename
        }
        return render_template('user/news_detail.html', news_item=news_item)
    except Exception as e:
        current_app.logger.error(f"Error parsing {filename}: {e}")
        return redirect(url_for('user.news'))

@bp.route('/terms_of_service')
def terms_of_service():
    # 服务条款
    return render_template('user/terms_of_service.html')

@bp.route('/privacy_policy')
def privacy_policy():
    # 隐私政策
        return render_template('user/privacy_policy.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username', '')
            password = request.form.get('password', '')
            qq_group_id = 962669723 # 强制某个QQ群成员才能使用request.form.get('qq_group_id', '')
            invite_code = request.form.get('invite_code', '')
            qqid = ""
            if not username.isascii():
                flash('用户名只能包含 ASCII(英文、数字、符号) 码！')
                return render_template('user/register.html')
            try:
                now = datetime.now()
                minute_block = now.minute // 5
                key = f"{minute_block}{now.hour}{now.date()}{minute_block}".encode()
                invite_bytes = bytes.fromhex(invite_code)
                xor_result = [i ^ j for i, j in zip(invite_bytes, key)]
                qqid_bytes = bytes(b - 6 for b in xor_result)
                qqid = qqid_bytes.decode().rstrip('#')
                if not qqid.isdigit():
                    flash('无效的临时密钥')
                    return render_template('user/register.html')
                with sqlite3.connect('./web/user.db') as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT is_banned FROM user WHERE qq_number = ? AND qq_group_id = ?", (qqid, qq_group_id))
                    res = cursor.fetchone()
                    if not res or res[0] == 1:
                        flash('身份认证失败')
                        return render_template('user/register.html')
            except ValueError:
                flash('无效的临时密钥')
                return render_template('user/register.html')
            except UnicodeDecodeError:
                flash('无效的临时密钥')
                return render_template('user/register.html')
            except Exception as e:
                current_app.logger.warning(f'临时密钥处理错误: {str(e)}')
                flash('无效的临时密钥')
                return render_template('user/register.html')
            with Connect() as c:
                try:
                    new_user = UserRegister(c)
                    new_user.set_name(username)
                    new_user.set_password(password)
                    new_user.set_email(f"{qqid}@qq.com")
                    ip = request.remote_addr
                    device_id = request.headers.get('User-Agent')
                    new_user.register(device_id, ip)
                    flash('恭喜您，注册成功！')
                    return render_template('user/index.html')
                except DataExist as e:
                    flash(f'注册失败: {e.message}')
                    current_app.logger.info(f'注册数据已存在: {e.message}, 代码: {e.code}')
                except InputError as e:
                    flash(f'注册失败: {e.message}')
                    current_app.logger.warning(f'注册输入错误: {e.message}')
                except Exception as e:
                    flash('注册过程中发生错误，请稍后重试')
                    current_app.logger.error(f'注册异常: {str(e)}', exc_info=True)
        except Exception as e:
            flash('请求过于频繁，请稍后再试')
            current_app.logger.warning(f'注册请求限流: {str(e)}')
    return render_template('user/register.html')

@bp.route('/viewing_textures', methods=['GET', 'POST'])
def viewing_textures():
    # 定义材质文件夹的基础路径
    base_dir = os.path.join(os.path.dirname(__file__), '..',  'static', 'viewing_textures')
    providers = []
    if os.path.exists(base_dir) and os.path.isdir(base_dir):
        for provider_name in os.listdir(base_dir):
            provider_path = os.path.join(base_dir, provider_name)
            if not os.path.isdir(provider_path):
                continue
            images = []
            for filename in os.listdir(provider_path):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                    image_url = f'/static/viewing_textures/{provider_name}/{filename}'
                    images.append({
                        'filename': filename,
                        'url': image_url,
                        'size': f"{os.path.getsize(os.path.join(provider_path, filename)) // 1024} KB" 
                    })
            images.sort(key=lambda x: x['filename'])
            providers.append({
                'name': provider_name,
                'image_count': len(images),
                'images': images
            })
        providers.sort(key=lambda x: x['name'])
    return render_template('user/viewing_textures.html', providers=providers)

@bp.route('/me', methods=['GET', 'POST'])
def me():
    user = None
    banner_items = []
    products_list = []  # 初始化产品列表
    # 查询所有商品并转换为字典列表（修复核心问题）
    with sqlite3.connect('./web/user.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM store_item") 
        products = cursor.fetchall() 
        products_list = [dict(product) for product in products]

    # 处理POST请求
    if request.method == 'POST':
        action = request.form.get('action', '')
        if not action:
            try:
                username = request.form.get('username', '')
                tmpkey = request.form.get('tmpkey', '')
                now = datetime.now()
                minute_block = now.minute // 5
                key = f"{minute_block}{now.hour}{now.date()}{minute_block}".encode()
                invite_bytes = bytes.fromhex(tmpkey)
                xor_result = [i ^ j for i, j in zip(invite_bytes, key)]
                qqid_bytes = bytes(b - 6 for b in xor_result)
                qqid = qqid_bytes.decode().rstrip('#')
                
                with Connect() as c:
                    c.row_factory = sqlite3.Row
                    c.execute("SELECT * FROM user WHERE email=?", (qqid + "@qq.com",))
                    user = c.fetchone()
                    if not user or user['name'] != username:
                        flash('身份认证失败！')
                        return render_template('user/me.html', user=None, banner_items=[], products=products_list)
                    session['user_page_user_id'] = user['user_id']
            except:
                flash(f'身份认证失败：请输入有效的临时密钥！')
                return render_template('user/me.html', user=None, banner_items=[], products=products_list)
        
        elif action == 'change_password':
            user_id = session.get('user_page_user_id')
            new_pwd = request.form.get('new_password')
            confirm_pwd = request.form.get('confirm_password')
            
            if not user_id:
                flash('请先登录！')
                return render_template('user/me.html', user=user, banner_items=banner_items, products=products_list)
                
            with Connect() as c:
                c.row_factory = sqlite3.Row
                c.execute("SELECT * FROM user WHERE user_id=?", (user_id,))
                user = c.fetchone()
                
                if not user:
                    flash('用户不存在！')
                elif new_pwd != confirm_pwd:
                    flash('两次输入的新密码不一致！')
                else:
                    hash_pwd = hashlib.sha256(new_pwd.encode("utf8")).hexdigest()
                    c.execute("UPDATE user SET password=? WHERE user_id=?", (hash_pwd, user_id))
                    conn.commit()  # 提交事务
                    flash('密码修改成功！')
                c.execute("SELECT * FROM user WHERE user_id=?", (user_id,))
                user = c.fetchone()

        elif action == 'change_username':
            user_id = session.get('user_page_user_id')
            new_username = request.form.get('new_username')
            if not user_id:
                flash('请先登录！')
                return render_template('user/me.html', user=user, banner_items=banner_items, products=products_list)
            with Connect() as c:
                c.row_factory = sqlite3.Row
                c.execute("SELECT * FROM user WHERE user_id=?", (user_id,))
                user = c.fetchone()
                if not user:
                    flash('用户不存在！')
                elif user["ticket"] < 648:
                    flash('余额不足！')
                elif not new_username.isascii():
                    flash('新用户名只能包含 ASCII(英文、数字、符号) 码！')
                elif new_username == user['name']:
                    flash('新用户名不能与原用户名相同！')
                else:
                    with Connect() as cc:
                        cc.row_factory = sqlite3.Row
                        cc.execute("SELECT * FROM user WHERE name=?", (new_username,))
                        if cc.fetchone():
                            flash('用户名已存在！')
                        else:
                            c.execute("UPDATE user SET name=?, ticket=ticket-648 WHERE user_id=?", (new_username, user_id))
                            conn.commit()
                            flash('购买成功！')
                with Connect() as cc:
                    c.row_factory = sqlite3.Row
                    c.execute("SELECT * FROM user WHERE user_id=?", (user_id,))
                    user = c.fetchone()
        
        elif action == 'bankrupt':
            user_id = session.get('user_page_user_id')
            new_username = request.form.get('new_username')
            if not user_id:
                flash('请先登录！')
                return render_template('user/me.html', user=user, banner_items=banner_items, products=products_list)
            with Connect() as c:
                c.row_factory = sqlite3.Row
                c.execute("SELECT * FROM user WHERE user_id=?", (user_id,))
                user = c.fetchone()
                if user['ticket'] >= 0:
                    flash('暂未达到申请破产的条件！')
                else:
                    delta = 0 - user['ticket']
                    present_id_1 = '破产申请1' + str(user_id)
                    present_id_2 = '破产申请2' + str(user_id)
                    try:
                        c.execute("INSERT INTO present(present_id, expire_ts, description) VALUES (?, ?, ?)", (present_id_1, (int((time.time() + 86400) * 1000)), '破产申请：你必须扣除残片后才能获取破产补助'))
                        c.execute("INSERT INTO present(present_id, expire_ts, description) VALUES (?, ?, ?)", (present_id_2, (int((time.time() + 86400) * 1000)), '破产申请成功，请尽快领取！'))
                        c.execute("INSERT INTO present_item(present_id, item_id, type, amount) VALUES (?, 'fragment', 'fragment', ?)", (present_id_1, -1000))
                        c.execute("INSERT INTO present_item(present_id, item_id, type, amount) VALUES (?, 'memory', 'memory', ?)", (present_id_2, delta))
                    except:
                        c.execute("UPDATE present SET expire_ts=? WHERE present_id=? OR present_id=?", ((int((time.time() + 86400) * 1000)), present_id_1, present_id_2))
                        c.execute("UPDATE present_item SET amount=? WHERE present_id=?", (delta, present_id_2))
                    try:
                        c.execute("INSERT INTO user_present(user_id, present_id) VALUES (?, ?)", (user_id, present_id_1))
                        c.execute("INSERT INTO user_present(user_id, present_id) VALUES (?, ?)", (user_id, present_id_2))
                    except Exception as e:
                        flash(f'申请失败：你已经申请破产了!')
                    else:
                        flash('申请成功：请尽快登陆游戏领取！')
                    conn.commit()
                with Connect() as cc:
                    c.row_factory = sqlite3.Row
                    c.execute("SELECT * FROM user WHERE user_id=?", (user_id,))
                    user = c.fetchone()

        elif action == 'fragment_exchange':
            user_id = session.get('user_page_user_id')
            frag_num = int(request.form.get('fragments'))
            if not user_id:
                flash('请先登录！')
                return render_template('user/me.html', user=user, banner_items=banner_items, products=products_list)
            with Connect() as c:
                c.row_factory = sqlite3.Row
                c.execute("SELECT * FROM user WHERE user_id=?", (user_id,))
                user = c.fetchone()
                if user['ticket'] < frag_num:
                    flash('余额不足！')
                else:
                    present_id_1 = '残片兑换1' + str(user_id)
                    present_id_2 = '残片兑换2' + str(user_id)
                    try:
                        c.execute("INSERT INTO present(present_id, expire_ts, description) VALUES (?, ?, ?)", (present_id_1, (int((time.time() + 86400) * 1000)), '残片兑换：请先支付虚实构想!'))
                        c.execute("INSERT INTO present(present_id, expire_ts, description) VALUES (?, ?, ?)", (present_id_2, (int((time.time() + 86400) * 1000)), '残片兑换：请尽快领取兑换的残片！'))
                        c.execute("INSERT INTO present_item(present_id, item_id, type, amount) VALUES (?, 'memory', 'memory', ?)", (present_id_1, -1 * frag_num))
                        
                        c.execute("INSERT INTO present_item(present_id, item_id, type, amount) VALUES (?, 'fragment', 'fragment', ?)", (present_id_2, frag_num))
                    except:
                        c.execute("UPDATE present SET expire_ts=? WHERE present_id=? OR present_id=?", ((int((time.time() + 86400) * 1000)), present_id_1, present_id_2))
                        c.execute("UPDATE present_item SET amount=? WHERE present_id=?", (-1 * frag_num, present_id_1))
                        c.execute("UPDATE present_item SET amount=? WHERE present_id=?", (frag_num, present_id_2))
                    try:
                        c.execute("INSERT INTO user_present(user_id, present_id) VALUES (?, ?)", (user_id, present_id_2))
                        c.execute("INSERT INTO user_present(user_id, present_id) VALUES (?, ?)", (user_id, present_id_1))
                    except Exception as e:
                        flash(f'兑换失败：你已经兑换过了!')
                    else:
                        flash('兑换成功：请尽快登录游戏领取！')
                    conn.commit()
                with Connect() as cc:
                    c.row_factory = sqlite3.Row
                    c.execute("SELECT * FROM user WHERE user_id=?", (user_id,))
                    user = c.fetchone()

        elif action == 'update_banner':
            user_id = session.get('user_page_user_id')
            selected_id = request.form.get('banner_id', '').lstrip('_')
            
            if not user_id:
                flash('请先登录！')
                return render_template('user/me.html', user=user, banner_items=banner_items, products=products_list)
            
            with Connect() as c:

                c.execute("SELECT item_id FROM user_item WHERE user_id=? AND type IN ('course_banner', '_course_banner')", (user_id,))
                all_items = [row[0] for row in c.fetchall()]
                
                for item in all_items:
                    cleaned_item = item.lstrip('_')
                    if cleaned_item == selected_id:
                        c.execute("UPDATE user_item SET item_id=?, type='course_banner' WHERE user_id=? AND item_id=?", 
                                 (cleaned_item, user_id, item))
                    else:
                        new_item_id = f"_{cleaned_item}"
                        c.execute("UPDATE user_item SET item_id=?, type='_course_banner' WHERE user_id=? AND item_id=?", 
                                 (new_item_id, user_id, item))
                conn.commit()  # 提交事务
                flash('段位框设置已保存！')
                c.row_factory = sqlite3.Row
                c.execute("SELECT * FROM user WHERE user_id=?", (user_id,))
                user = c.fetchone()

    # 获取用户信息和banner项目
    if user:
        with Connect() as c:
            c.execute("SELECT item_id FROM user_item WHERE user_id=? AND type IN ('course_banner', '_course_banner')", (user['user_id'],))
            banner_items = [i[0] for i in c.fetchall()]
    return render_template('user/me.html', user=user, banner_items=banner_items, products=products_list)

@bp.route('/search-users')
def search_users():
    query = request.args.get('query', '').lower()
    with Connect() as c:
        c.row_factory = sqlite3.Row
        # 优化查询：添加LIMIT防止数据过多，使用LIKE在数据库层面过滤
        c.execute("SELECT * FROM user WHERE name LIKE ? LIMIT 20", (f'%{query}%',))
        users = c.fetchall()
    
    # 转换为字典列表
    user_list = [dict(user) for user in users]
    return jsonify(user_list)

@bp.route('/purchase', methods=['POST'])
def purchase():
    if 'user_page_user_id' not in session:
        return jsonify({"success": False, "message": "请先登录"})
    
    user_id = session['user_page_user_id']
    data = request.json
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))
    
    # 1. 查询商品信息
    with sqlite3.connect('./web/user.db', timeout=10) as userdbc:
        userdbc.row_factory = sqlite3.Row
        usercur = userdbc.cursor()
        usercur.execute("SELECT * FROM store_item WHERE id=?", (product_id,)) 
        product_row = usercur.fetchone()
        
        if not product_row:
            return jsonify({"success": False, "message": "商品不存在"})
        product = dict(product_row)
    
    # 2. 检查库存和购买限制
    if quantity <= 0:
        return jsonify({"success": False, "message": "购买数量必须大于0"})
    if product['stock'] != -1 and product['stock'] < quantity:
        return jsonify({"success": False, "message": "库存不足"})
    if product.get('limit') and quantity > product['limit']:
        return jsonify({"success": False, "message": f"超过单次购买限制，最多可购买{product['limit']}个"})
    
    # 3. 处理购买逻辑
    total_price = product['price'] * quantity
    with Connect() as gamecur:  # 假设Connect()是数据库连接方法
        gamecur.row_factory = sqlite3.Row
        
        # 检查用户余额
        gamecur.execute("SELECT ticket FROM user WHERE user_id=?", (user_id,))
        user_ticket = gamecur.fetchone()
        if not user_ticket or user_ticket['ticket'] < total_price:
            return jsonify({"success": False, "message": "余额不足"})
        
        # 4. 清理所有过期礼物（只处理present和present_item）
        current_ts = int(time.time() * 1000)  # 当前时间戳（毫秒）
        
        # 获取所有已过期的商店购买类礼物ID
        gamecur.execute("""
            SELECT present_id FROM present 
            WHERE description LIKE '商店购买：%' 
              AND expire_ts < ? 
        """, (current_ts,))
        
        expired_present_ids = [row['present_id'] for row in gamecur.fetchall()]
        
        if expired_present_ids:
            # 1) 先删除present_item中关联的记录
            placeholders = ', '.join('?' for _ in expired_present_ids)
            gamecur.execute(f"""
                DELETE FROM present_item 
                WHERE present_id IN ({placeholders})
            """, expired_present_ids)
            
            # 2) 再删除present中的过期记录
            gamecur.execute(f"""
                DELETE FROM present 
                WHERE present_id IN ({placeholders})
            """, expired_present_ids)
        
        # 5. 检查用户是否有未完成的订单（通过user_present关联检查）
        gamecur.execute("""
            SELECT 1 FROM user_present 
            WHERE user_id = ? 
              AND present_id IN (
                  SELECT present_id FROM present 
                  WHERE description LIKE '商店购买：%'
                    AND expire_ts >= ?
              )
        """, (user_id, current_ts))
        if gamecur.fetchone():
            return jsonify({"success": False, "message": "你有一笔订单未完成，请先领取后再购买！"})
        
        # 6. 生成唯一订单ID
        timestamp = int(time.time() * 1000)
        random_suffix = random.randint(1000, 9999)
        present_id = f"store_{user_id}_{timestamp}_{random_suffix}"
        
        # 7. 更新库存
        with sqlite3.connect('./web/user.db', timeout=10) as userdbc_update:
            usercur_update = userdbc_update.cursor()
            if product['stock'] != -1:
                usercur_update.execute(
                    "UPDATE store_item SET stock = stock - ? WHERE id = ?", 
                    (quantity, product_id)
                )
                userdbc_update.commit()
        
        # 8. 创建新订单记录
        expire_ts = int((time.time() + 86400) * 1000)  # 24小时后过期
        description = f"商店购买：{product['name']}"
        
        gamecur.execute(
            "INSERT INTO present(present_id, expire_ts, description) VALUES (?, ?, ?)",
            (present_id, expire_ts, description)
        )
        gamecur.execute(
            "INSERT INTO present_item(present_id, item_id, type, amount) VALUES (?, ?, ?, ?)",
            (present_id, product['item_id'], product['item_type'], quantity)
        )
        gamecur.execute(
            "INSERT INTO user_present(user_id, present_id) VALUES (?, ?)",
            (user_id, present_id)
        )
        gamecur.execute(
            "UPDATE user SET ticket = ticket - ? WHERE user_id=?",
            (total_price, user_id)
        )
    
    return jsonify({
        "success": True,
        "message": f"支付成功！成功购买 {quantity} 个 {product['name']}",
        "total_price": total_price
    })


@bp.route('/gift', methods=['POST'])
def gift():
    return jsonify({"success": False, "message": "暂未开放"})
    if 'user_page_user_id' not in session:
        return jsonify({"success": False, "message": "请先登录"})
    user_id = session['user_page_user_id']
    data = request.json
    product_id = data.get('product_id')
    recipient_username = data.get('recipient')
    quantity = int(data.get('quantity', 1))  # 默认为1，支持指定数量
    
    # 查询商品信息
    with sqlite3.connect('./web/user.db', timeout=10) as userdbc:
        userdbc.row_factory = sqlite3.Row
        usercur = userdbc.cursor()
        usercur.execute("SELECT * FROM store_item WHERE id=?", (product_id,))
        product_row = usercur.fetchone()
        if not product_row:
            return jsonify({"success": False, "message": "商品不存在"})
        product = dict(product_row)
    
    # 查找接收者信息
    with Connect() as gamecur:
        gamecur.row_factory = sqlite3.Row
        gamecur.execute("SELECT * FROM user WHERE name = ?", (recipient_username,))
        recipient = gamecur.fetchone()
        if not recipient:
            return jsonify({"success": False, "message": "接收者不存在"})
        recipient_id = recipient['user_id']
    
    # 检查不能赠送给自己
    if recipient_id == user_id:
        return jsonify({"success": False, "message": "不能赠送给自己"})
    
    # 检查数量和库存限制
    if quantity <= 0:
        return jsonify({"success": False, "message": "赠送数量必须大于0"})
    if product['stock'] != -1 and product['stock'] < quantity:
        return jsonify({"success": False, "message": "库存不足"})
    if product.get('limit') and quantity > product['limit']:
        return jsonify({"success": False, "message": f"超过单次赠送限制，最多可赠送{product['limit']}个"})
    
    # 检查赠送者余额
    total_price = product['price'] * quantity
    with Connect() as gamecur:
        gamecur.row_factory = sqlite3.Row
        gamecur.execute("SELECT * FROM user WHERE user_id=?", (user_id,))
        user_info = dict(gamecur.fetchone())
        if user_info['ticket'] < total_price:
            return jsonify({"success": False, "message": "余额不足"})
        
        # 更新商品库存
        if product['stock'] != -1:
            usercur.execute("UPDATE store_item SET stock = stock - ? WHERE id = ?", (quantity, product_id))
            userdbc.commit()
        
        # 生成礼物标识
        gift_present = f"礼物_{user_id}_{recipient_id}"
        
        # 检查接收者是否有未领取的相同礼物订单
        gamecur.execute("SELECT 1 FROM user_present WHERE user_id=? AND present_id=?", (recipient_id, gift_present))
        if gamecur.fetchone():
            return jsonify({"success": False, "message": "接收者有未领取的相同礼物，请稍后再试！"})
        
        # 处理礼物记录
        try:
            gamecur.execute("INSERT INTO present(present_id, expire_ts, description) VALUES (?, ?, ?)", 
                          (gift_present, int((time.time() + 86400) * 1000), f"收到来自用户{user_info['name']}的赠送：{product['name']}"))
            gamecur.execute("INSERT INTO present_item(present_id, item_id, type, amount) VALUES (?, ?, ?, ?)", 
                          (gift_present, product_row['item_id'], product_row['item_type'], quantity))
        except:
            gamecur.execute("UPDATE present SET expire_ts=?, description=? WHERE present_id=?", 
                          (int((time.time() + 86400) * 1000), f"收到来自用户{user_info['name']}的赠送：{product['name']}", gift_present))
            gamecur.execute("UPDATE present_item SET amount=? WHERE present_id=? AND item_id=? AND type=?", 
                          (quantity, gift_present, product_row['item_id'], product_row['item_type']))
        
        # 关联接收者与礼物
        gamecur.execute("INSERT INTO user_present(user_id, present_id) VALUES (?, ?)", (recipient_id, gift_present))
        
        # 扣减赠送者余额
        gamecur.execute("UPDATE user SET ticket = ticket - ? WHERE user_id=?", (total_price, user_id))
    
    return jsonify({
        "success": True,
        "message": f"成功向 {recipient_username} 赠送 {quantity} 个 {product['name']}",
        "total_price": total_price
    })