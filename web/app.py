"""
票多多 - Flask Web 应用（方案 C：混合策略）
路由：首页/搜索/图表/关注列表/开票日历/API 接口
"""

import sys
import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, redirect, url_for, flash

# 添加项目根路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.piaoduoduo import PiaoDuoDuo


app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['JSON_AS_ASCII'] = False
app.config['SECRET_KEY'] = 'piaoduoduo-secret-key'


# 全局应用实例
_pdd = None


def get_pdd():
    """获取或创建票多多应用实例"""
    global _pdd
    if _pdd is None:
        _pdd = PiaoDuoDuo(mode="sample")
    return _pdd


# ============== 页面路由 ==============

@app.route('/')
def index():
    """首页 - 搜索框 + 统计"""
    pdd = get_pdd()
    stats = pdd.get_stats()
    watchlist = pdd.get_watchlist()[:5]
    upcoming_sales = pdd.get_upcoming_sales(7)

    return render_template('index.html',
                           stats=stats,
                           watchlist=watchlist,
                           upcoming_sales=upcoming_sales,
                           app_name="票多多 - 演唱会资讯聚合与关注工具")


@app.route('/search', methods=['GET', 'POST'])
def search():
    """搜索结果页 - 展示演出列表"""
    keyword = ""
    city = ""
    mode = "auto"  # 默认为自动模式，优先尝试真实采集

    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        city = request.form.get('city', '').strip()
        mode = request.form.get('mode', 'auto')
    else:
        keyword = request.args.get('keyword', '').strip()
        city = request.args.get('city', '').strip()
        mode = request.args.get('mode', 'auto')

    if not keyword:
        # 无关键词时，重定向到首页
        return redirect(url_for('index'))

    pdd = get_pdd()
    # 设置采集模式
    pdd.damai.mode = mode
    pdd.maoyan.mode = mode
    pdd.piaoxingqiu.mode = mode
    pdd.social_media.mode = mode

    # 示例模式：使用用户输入的关键词而非固定的周杰伦
    if mode == "sample":
        result = pdd.load_sample_data(keyword)
    else:
        result = pdd.run_full_workflow(keyword, city=city, limit=20)

    # 获取开票提醒
    upcoming_sales = pdd.get_upcoming_sales(7)

    return render_template('search_result.html',
                           result=result,
                           keyword=keyword,
                           city=city,
                           mode=mode,
                           upcoming_sales=upcoming_sales)


@app.route('/watchlist')
def watchlist_page():
    """我的关注 - 展示关注的演出列表"""
    pdd = get_pdd()
    watchlist = pdd.get_watchlist()

    # 获取即将开票的演出
    upcoming_sales = pdd.get_upcoming_sales(30)
    stats = pdd.get_stats()

    return render_template('watchlist.html',
                           watchlist=watchlist,
                           upcoming_sales=upcoming_sales,
                           stats=stats)


@app.route('/calendar')
def sale_calendar():
    """开票日历 - 展示未来 30 天的开票时间"""
    pdd = get_pdd()
    calendar = pdd.get_sale_calendar(30)
    upcoming_sales = pdd.get_upcoming_sales(7)

    return render_template('calendar.html',
                           calendar=calendar,
                           upcoming_sales=upcoming_sales)


@app.route('/charts')
def charts_page():
    """图表页 - 数据可视化"""
    pdd = get_pdd()
    # 从数据库获取最新数据
    events = pdd.get_from_db(limit=50)
    event_dicts = []
    for e in events:
        try:
            event_dicts.append(e.to_dict())
        except Exception:
            pass

    if not event_dicts:
        sample_data = pdd.load_sample_data("周杰伦")
        event_dicts = sample_data.get('events', [])

    # 准备可视化数据
    visualization = pdd.visualize(events)
    stats = pdd.get_stats()

    return render_template('charts.html',
                           visualization=visualization,
                           stats=stats,
                           events=event_dicts,
                           result={'events': event_dicts, 'summary': stats})


@app.route('/event/<event_id>')
def event_detail(event_id):
    """演出详情页 - 可编辑票价信息"""
    pdd = get_pdd()
    event_data = pdd.get_event_detail(event_id)
    if not event_data:
        return render_template('404.html'), 404

    tickets = pdd.get_event_tickets(event_id)
    upcoming_sales = pdd.get_upcoming_sales(7)

    return render_template('event_detail.html',
                           event=event_data,
                           tickets=tickets,
                           upcoming_sales=upcoming_sales)


@app.route('/demo')
def demo_page():
    """演示页 - 功能全面展示"""
    pdd = get_pdd()
    result = pdd.load_sample_data("周杰伦")
    watchlist = pdd.get_watchlist()
    upcoming_sales = pdd.get_upcoming_sales(30)
    return render_template('demo.html',
                           result=result,
                           watchlist=watchlist,
                           upcoming_sales=upcoming_sales)


# ============== 操作路由（POST） ==============

@app.route('/watchlist/add', methods=['POST'])
def watchlist_add():
    """添加关注"""
    event_id = request.form.get('event_id', '')
    if not event_id:
        return jsonify({'success': False, 'message': '缺少演出 ID'})

    user_notes = request.form.get('notes', '')
    priority = int(request.form.get('priority', 0))

    pdd = get_pdd()
    success = pdd.add_to_watchlist(event_id, user_notes, priority)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': '已添加关注' if success else '添加失败'})
    return redirect(url_for('watchlist_page'))


@app.route('/watchlist/remove', methods=['POST'])
def watchlist_remove():
    """取消关注"""
    event_id = request.form.get('event_id', '')
    if not event_id:
        return jsonify({'success': False, 'message': '缺少演出 ID'})

    pdd = get_pdd()
    pdd.remove_from_watchlist(event_id)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': '已取消关注'})
    return redirect(url_for('watchlist_page'))


@app.route('/tickets/edit', methods=['POST'])
def tickets_edit():
    """编辑票价 - 手动更新票价信息"""
    event_id = request.form.get('event_id', '')
    if not event_id:
        return jsonify({'success': False, 'message': '缺少演出 ID'})

    # 解析票价数据
    prices = request.form.getlist('price[]')
    seat_types = request.form.getlist('seat_type[]')
    statuses = request.form.getlist('ticket_status[]')
    platforms = request.form.getlist('platform[]')

    tickets_data = []
    for i in range(len(prices)):
        try:
            price = float(prices[i])
            if price <= 0:
                continue
            tickets_data.append({
                'price': price,
                'seat_type': seat_types[i] if i < len(seat_types) else '',
                'ticket_status': statuses[i] if i < len(statuses) else '在售',
                'platform': platforms[i] if i < len(platforms) else ''
            })
        except (ValueError, TypeError):
            continue

    pdd = get_pdd()
    success = pdd.update_event_tickets(event_id, tickets_data)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success,
                        'message': '票价信息已更新' if success else '更新失败，请检查数据格式'})

    # 普通表单提交：跳回详情页
    return redirect(url_for('event_detail', event_id=event_id))


# ============== API 接口 ==============

@app.route('/api/search')
def api_search():
    """搜索 API - 返回 JSON 结果"""
    keyword = request.args.get('keyword', '演唱会').strip()
    city = request.args.get('city', '').strip()
    limit = int(request.args.get('limit', 20))
    mode = request.args.get('mode', 'sample')

    pdd = get_pdd()
    pdd.damai.mode = mode
    pdd.maoyan.mode = mode

    result = pdd.run_full_workflow(keyword, city=city, limit=limit)
    return jsonify(result)


@app.route('/api/watchlist')
def api_watchlist():
    """关注列表 API"""
    pdd = get_pdd()
    watchlist = pdd.get_watchlist()
    return jsonify({'success': True, 'watchlist': watchlist, 'total': len(watchlist)})


@app.route('/api/stats')
def api_stats():
    """统计信息 API"""
    pdd = get_pdd()
    return jsonify(pdd.get_stats())


@app.route('/api/upcoming')
def api_upcoming_sales():
    """即将开票 API - 返回未来 N 天内开票的演出列表"""
    days = int(request.args.get('days', 7))
    pdd = get_pdd()
    upcoming = pdd.get_upcoming_sales(days)
    return jsonify({'success': True, 'upcoming_sales': upcoming, 'total': len(upcoming)})


@app.route('/api/event/<event_id>')
def api_event_detail(event_id):
    """演出详情 API"""
    pdd = get_pdd()
    event = pdd.get_event_detail(event_id)
    if not event:
        return jsonify({'success': False, 'message': '未找到演出'})
    tickets = pdd.get_event_tickets(event_id)
    return jsonify({'success': True, 'event': event, 'tickets': tickets})


@app.route('/api/availability')
def api_availability():
    """开票状态 API"""
    keyword = request.args.get('keyword', '')
    pdd = get_pdd()
    availability = pdd.check_ticket_availability(keyword)
    return jsonify(availability)


# ============== 导出功能 ==============

@app.route('/export/csv')
def export_csv():
    """导出 CSV"""
    keyword = request.args.get('keyword', '')
    pdd = get_pdd()

    # 从数据库获取数据
    events = pdd.get_from_db(keyword=keyword, limit=100)
    if not events:
        result = pdd.load_sample_data(keyword or "周杰伦")
        events_dict = result.get('events', [])
    else:
        events_dict = [e.to_dict() for e in events]

    # 生成 CSV 内容
    csv_lines = ["演出标题,城市,场馆,演出时间,最低票价,来源平台,关注状态"]
    for e in events_dict:
        title = str(e.get('title', '')).replace(',', '，')
        city = str(e.get('city', '')).replace(',', '，')
        venue = str(e.get('venue', '')).replace(',', '，')
        date_str = str(e.get('date_str', '')).replace(',', '，')
        min_price = str(e.get('min_price', 0))
        platform = str(e.get('source_platform', ''))
        is_watching = "已关注" if e.get('is_watching', False) else ""
        csv_lines.append(f"{title},{city},{venue},{date_str},{min_price},{platform},{is_watching}")

    csv_content = '\n'.join(csv_lines)
    return Response(
        csv_content.encode('utf-8-sig'),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="piaoduoduo_{keyword or "all"}.csv"'}
    )


# ============== 错误处理 ==============

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('404.html', message="服务器内部错误"), 500


if __name__ == '__main__':
    print("🚀 票多多 Web 服务启动中...")
    print("📱 访问 http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
