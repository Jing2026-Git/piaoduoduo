#!/usr/bin/env python3
"""
票多多 - 命令行工具
用法:
    python cli.py search "周杰伦"
    python cli.py search "周杰伦" --city 北京
    python cli.py search "演唱会" --limit 30
    python cli.py demo                    # 使用示例数据
    python cli.py export --format csv     # 导出为CSV
    python cli.py export --format json    # 导出为JSON
    python cli.py stats                   # 查看统计信息
    python cli.py web                     # 启动演示网页
"""

import argparse
import sys
import os
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.piaoduoduo import PiaoDuoDuo


def cmd_search(args):
    """搜索命令: 从各平台采集演唱会信息"""
    print("=" * 60)
    print("🎫 票多多 - 演唱会票价智能比价工具")
    print("=" * 60)
    print()

    # 如果指定了 demo，则使用示例数据模式
    mode = "sample" if args.demo else "auto"

    app = PiaoDuoDuo(mode=mode)

    # 执行搜索
    events = app.search(args.keyword, city=args.city, limit=args.limit)

    if not events:
        print("❌ 没有找到相关演出数据")
        return

    # 显示结果摘要
    print("\n" + "=" * 60)
    print(f"📊 搜索结果汇总 (关键词: '{args.keyword}')")
    print("=" * 60)

    # 显示每一场演出
    for idx, event in enumerate(events[:args.display], 1):
        print(f"\n{'=' * 58}")
        print(f"{idx}. {event.title}")
        print(f"   🎤 {event.artist} | 📍 {event.city} - {event.venue}")
        print(f"   📅 {event.date_str}")

        # 显示票价信息
        if event.tickets:
            prices = [t for t in event.tickets]
            min_price = min(t.price for t in prices)
            max_price = max(t.price for t in prices)

            # 按平台分组显示
            platform_tickets = {}
            for t in event.tickets:
                if t.platform not in platform_tickets:
                    platform_tickets[t.platform] = []
                platform_tickets[t.platform].append(t)

            print(f"   💰 票价范围: ¥{int(min_price)} - ¥{int(max_price)}")
            for platform, tickets in sorted(platform_tickets.items()):
                platform_prices = sorted([int(t.price) for t in tickets])
                status = "✅ 有票" if any("售罄" not in t.ticket_status for t in tickets) else "❌ 已售罄"
                print(f"      {platform}: ¥{platform_prices[0]} 起 ({status})")

    # 简要统计
    summary = app.visualize(events).get('summary', {})
    if summary:
        print("\n" + "=" * 60)
        print("📈 数据统计")
        print("=" * 60)
        print(f"   共找到 {summary.get('total_events', 0)} 场演出")
        print(f"   {summary.get('total_tickets', 0)} 个票价档位")
        print(f"   覆盖 {summary.get('city_count', 0)} 个城市")
        print(f"   {summary.get('platform_count', 0)} 个售票平台")
        print(f"   平均票价: ¥{summary.get('avg_price', 0)}")
        print(f"   最低票价: ¥{summary.get('min_price', 0)}")
        print(f"   最高票价: ¥{summary.get('max_price', 0)}")

    # 提示导出
    print("\n💡 提示: 使用 'export' 子命令可导出详细数据")
    print("💡 提示: 使用 'web' 子命令可启动网页交互界面")


def cmd_compare(args):
    """票价对比命令"""
    print("=" * 60)
    print("🎫 票多多 - 票价智能对比")
    print("=" * 60)

    mode = "sample" if args.demo else "auto"
    app = PiaoDuoDuo(mode=mode)

    events = app.search(args.keyword, city=args.city, limit=args.limit)

    if not events:
        print("❌ 没有找到可对比的演出数据")
        return

    results = app.compare_prices(events)

    print(f"\n✅ 完成 {len(results)} 场演出票价对比:\n")

    for idx, result in enumerate(results, 1):
        print(f"{idx}. {result.event_title}")
        print(f"   📍 {result.city} {result.venue}")
        print(f"   📅 {result.date_str}")
        print(f"   ⬇️ 最低票价: ¥{int(result.min_price)} ({result.min_price_platform})")
        print(f"   ⬆️ 最高票价: ¥{int(result.max_price)}")

        # 显示各平台信息
        platform_list = result.platforms_with_data
        if platform_list:
            print(f"   🖥️  可购平台: {', '.join(platform_list)}")

        if result.recommendation:
            rec_line = result.recommendation.split('\n')[0]
            print(f"   💡 {rec_line}")
        print()


def cmd_export(args):
    """导出数据"""
    print(f"📦 正在导出 {args.format.upper()} 格式数据...")

    mode = "sample" if args.demo else "auto"
    app = PiaoDuoDuo(mode=mode)

    events = app.search(args.keyword, limit=args.limit)
    if not events:
        print("❌ 没有数据可导出")
        return

    comparison = app.compare_prices(events)

    # 生成输出文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    keyword_clean = args.keyword.replace(' ', '_')

    if args.output:
        output_file = args.output
    else:
        output_file = f"piaoduoduo_{keyword_clean}_{timestamp}.{args.format}"

    if args.format == "csv":
        app.export_csv(comparison, output_file)
    elif args.format == "json":
        app.export_json(comparison, output_file)

    print(f"✅ 导出完成: {output_file}")


def cmd_stats(args):
    """显示统计信息"""
    app = PiaoDuoDuo()
    stats = app.get_stats()

    print("=" * 60)
    print("📊 票多多 - 数据统计")
    print("=" * 60)
    print()
    print(f"   演出总数: {stats.get('event_count', 0)} 场")
    print(f"   票价档位: {stats.get('ticket_count', 0)} 个")
    print(f"   覆盖平台: {stats.get('platform_count', 0)} 个")
    print(f"   覆盖城市: {stats.get('city_count', 0)} 个")
    print(f"   历史记录: {stats.get('history_count', 0)} 条")
    print()
    print("💡 多次运行后可积累更多数据用于价格趋势分析")


def cmd_web(args):
    """启动网页界面"""
    print("🌐 启动票多多网页界面...")
    print(f"   请在浏览器中访问: http://localhost:{args.port}")
    print("   Ctrl+C 可停止服务")
    print()

    # 启动 Flask 应用
    from web.app import app as web_app
    web_app.run(host='0.0.0.0', port=args.port, debug=False)


def cmd_demo(args):
    """演示模式 - 一键展示完整功能"""
    print("=" * 60)
    print("🎫 票多多 - 演示模式")
    print("=" * 60)
    print("💡 使用示例数据展示完整功能（不依赖真实网络请求）")
    print()

    app = PiaoDuoDuo(mode="sample")
    result = app.load_sample_data(args.keyword)

    if not result.get('success'):
        print("❌ 演示加载失败")
        return

    print("\n" + "=" * 60)
    print("📊 演示结果")
    print("=" * 60)

    events = result['events']
    comparison = result['comparison']
    summary = result.get('summary', {})

    print(f"\n   搜索关键词: {result['keyword']}")
    print(f"   搜索时间: {result['search_time']}")
    print(f"   找到 {len(events)} 场演出")
    print(f"   覆盖 {summary.get('city_count', 0)} 个城市")
    print(f"   {summary.get('platform_count', 0)} 个售票平台")
    print(f"   平均票价: ¥{summary.get('avg_price', 0)}")

    print(f"\n{'=' * 60}")
    print("💡 Top 5 性价比推荐")
    print(f"{'=' * 60}")

    for idx, r in enumerate(comparison[:5], 1):
        print(f"\n{idx}. {r['event_title']}")
        print(f"   💰 最低 ¥{int(r.get('min_price', 0))} ({r.get('min_price_platform', '')})")
        print(f"   📍 {r.get('city', '')} | 📅 {r.get('date_str', '')}")
        rec = r.get('recommendation', '').split('\n')[0]
        print(f"   💡 {rec}")

    print(f"\n{'=' * 60}")
    print("✅ 演示完成！")
    print(f"{'=' * 60}")
    print("\n📦 启动网页界面可查看图表和更多详情:")
    print("   python cli.py web")
    print("\n📦 也可导出为文件:")
    print("   python cli.py export --keyword " + args.keyword + " --format csv")


def main():
    parser = argparse.ArgumentParser(
        prog='piaoduoduo',
        description='🎫 票多多 - 演唱会票价智能比价与资讯追踪工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python cli.py search "周杰伦"           搜索周杰伦演唱会
  python cli.py search "演唱会" --city 北京   搜索北京的演唱会
  python cli.py compare "周杰伦"          对比各平台票价
  python cli.py demo                      使用示例数据演示完整功能
  python cli.py export --keyword "演唱会"  导出数据
  python cli.py web                       启动网页交互界面
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # search 子命令
    search_parser = subparsers.add_parser('search', help='搜索演出信息')
    search_parser.add_argument('keyword', type=str, help='搜索关键词')
    search_parser.add_argument('--city', type=str, default='', help='城市过滤')
    search_parser.add_argument('--limit', type=int, default=20, help='每个平台返回结果数量')
    search_parser.add_argument('--display', type=int, default=20, help='显示前N场演出')
    search_parser.add_argument('--demo', action='store_true', help='使用示例数据模式')

    # compare 子命令
    compare_parser = subparsers.add_parser('compare', help='票价智能对比')
    compare_parser.add_argument('keyword', type=str, help='搜索关键词')
    compare_parser.add_argument('--city', type=str, default='', help='城市过滤')
    compare_parser.add_argument('--limit', type=int, default=20, help='结果数量')
    compare_parser.add_argument('--demo', action='store_true', help='使用示例数据模式')

    # export 子命令
    export_parser = subparsers.add_parser('export', help='导出数据')
    export_parser.add_argument('--keyword', type=str, default='演唱会', help='搜索关键词')
    export_parser.add_argument('--format', type=str, choices=['csv', 'json'], default='csv', help='导出格式')
    export_parser.add_argument('--output', type=str, default='', help='输出文件路径')
    export_parser.add_argument('--limit', type=int, default=30, help='结果数量')
    export_parser.add_argument('--demo', action='store_true', help='使用示例数据模式')

    # stats 子命令
    stats_parser = subparsers.add_parser('stats', help='显示统计信息')

    # web 子命令
    web_parser = subparsers.add_parser('web', help='启动网页界面')
    web_parser.add_argument('--port', type=int, default=5000, help='服务端口')

    # demo 子命令
    demo_parser = subparsers.add_parser('demo', help='一键演示所有功能')
    demo_parser.add_argument('--keyword', type=str, default='周杰伦', help='演示关键词')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    command_handlers = {
        'search': cmd_search,
        'compare': cmd_compare,
        'export': cmd_export,
        'stats': cmd_stats,
        'web': cmd_web,
        'demo': cmd_demo,
    }

    handler = command_handlers.get(args.command)
    if handler:
        try:
            handler(args)
        except KeyboardInterrupt:
            print("\n\n👋 已退出")
        except Exception as e:
            print(f"\n❌ 执行出错: {e}")
            import traceback
            traceback.print_exc()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
