"""
票多多 - 演示网页 Flask 应用
支持:
- 关键词搜索，实时运行数据采集
- 票价图表可视化
- 演出详情展示
- 数据导出
"""

import sys
import os
import json
from datetime import datetime

from flask import Flask, render_template, request, jsonify, Response

# 添加项目根路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.piaoduoduo import PiaoDuoDuo


# 创建 Flask 应用
app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

app.config['JSON_AS_ASCII'] = False  # 确保中文能正常显示

# 全局应用实例
_pdd = None


def get_pdd():
    """获取或创建票多多应用实例"""
    global _pdd
    if _pdd is None:
        _pdd = PiaoDuoDuo(mode="auto")
    return _pdd


# ---------- 路由 ----------

@app.route('/')
def index():
    """首页 - 搜索界面和示例数据展示"""
    pdd = get_pdd()
    stats = pdd.get_stats()

    # 默认加载示例数据
    sample_data = pdd.load_sample_data("周杰伦")

    return render_template('index.html',
                           stats=stats,
                           sample_data=sample_data,
                           app_name="票多多")


@app.route('/search', methods=['GET', 'POST'])
def search():
    """搜索接口 - 处理用户关键词并返回结果"""
    keyword = ""

    if request.method == 'POST':
        # 表单提交
        keyword = request.form.get('keyword', '').strip()
        city = request.form.get('city', '').strip()
        limit = int(request.form.get('limit', 20))
        mode = request.form.get('mode', 'auto')
    else:
        # GET 请求
        keyword = request.args.get('keyword', '').strip()
        city = request.args.get('city', '').strip()
        limit = int(request.args.get('limit', 20))
        mode = request.args.get('mode', 'auto')

    if not keyword:
        keyword = "演唱会"

    pdd = get_pdd()
    pdd.damai.mode = mode
    pdd.maoyan.mode = mode

    # 执行完整工作流
    result = pdd.run_full_workflow(keyword, city=city, limit=limit)

    # 判断是否 AJAX 请求
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(result)

    # 正常页面请求
    return render_template('search_result.html',
                           result=result,
                           keyword=keyword,
                           city=city)


@app.route('/api/search')
def api_search():
    """API接口 - 返回JSON搜索结果"""
    keyword = request.args.get('keyword', '演唱会').strip()
    city = request.args.get('city', '').strip()
    limit = int(request.args.get('limit', 20))
    mode = request.args.get('mode', 'auto')

    pdd = get_pdd()
    pdd.damai.mode = mode
    pdd.maoyan.mode = mode

    result = pdd.run_full_workflow(keyword, city=city, limit=limit)
    return jsonify(result)


@app.route('/api/availability')
def api_availability():
    """API接口 - 检查开票状态"""
    keyword = request.args.get('keyword', '演唱会').strip()
    pdd = get_pdd()

    availability = pdd.check_ticket_availability(keyword)
    return jsonify(availability)


@app.route('/api/trend')
def api_trend():
    """API接口 - 获取价格趋势"""
    keyword = request.args.get('keyword', '').strip()
    event_id = request.args.get('event_id', '').strip()

    pdd = get_pdd()
    trend = pdd.get_price_trend(keyword, event_id)
    return jsonify(trend)


@app.route('/api/stats')
def api_stats():
    """API接口 - 获取统计信息"""
    pdd = get_pdd()
    stats = pdd.get_stats()
    return jsonify(stats)


@app.route('/export/<format>')
def export_data(format):
    """数据导出接口"""
    keyword = request.args.get('keyword', '演唱会')
    mode = request.args.get('mode', 'auto')

    pdd = get_pdd()
    pdd.damai.mode = mode
    pdd.maoyan.mode = mode

    events = pdd.search(keyword)
    comparison = pdd.compare_prices(events)

    if format == 'csv':
        content = pdd.comparator.to_csv(comparison)
        mime = 'text/csv; charset=utf-8-sig'
        filename = f'piaoduoduo_{keyword}_{datetime.now().strftime("%Y%m%d")}.csv'
    elif format == 'json':
        content = pdd.comparator.to_json(comparison)
        mime = 'application/json; charset=utf-8'
        filename = f'piaoduoduo_{keyword}_{datetime.now().strftime("%Y%m%d")}.json'
    else:
        return jsonify({'error': '不支持的格式'}), 400

    return Response(
        content,
        mimetype=mime,
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@app.route('/charts')
def charts():
    """图表展示页面"""
    keyword = request.args.get('keyword', '周杰伦')
    pdd = get_pdd()
    result = pdd.load_sample_data(keyword)
    return render_template('charts.html',
                           result=result,
                           keyword=keyword)


@app.route('/demo')
def demo():
    """演示页面 - 一键展示所有功能"""
    pdd = get_pdd()
    result = pdd.load_sample_data("周杰伦")
    return render_template('demo.html', result=result)


@app.errorhandler(404)
def page_not_found(e):
    """404页面"""
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    """500页面"""
    return render_template('500.html', error=str(e)), 500


if __name__ == '__main__':
    # 启动时初始化示例数据
    print("🎫 正在启动票多多网页服务...")
    print("   请在浏览器中访问: http://localhost:5000")

    app.run(host='0.0.0.0', port=5000, debug=True)
