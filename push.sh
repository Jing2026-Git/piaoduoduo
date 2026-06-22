#!/bin/bash
# 票多多 - 一键推送脚本
# 使用方法：在终端中运行此脚本

cd "$(dirname "$0")"

echo "📦 票多多推送脚本"
echo "=================="

# 检查是否有更改
if git diff --quiet && [ -z "$(git status --porcelain)" ]; then
    echo "✅ 没有需要推送的更改"
    exit 0
fi

# 添加所有更改
git add -A

# 创建提交
git commit -m "feat(方案C): 演出资讯聚合 + 用户关注 + 半自动票价 + 开票提醒

核心功能:
- 新增'我的关注'功能：搜索后可一键关注演出
- 新增'票价手动编辑'：用户可设置各票价档
- 新增'开票日历'：未来30天开票时间可视化
- 新增'演出详情页'：票价编辑 + 用户备注 + 优先级设置"

# 推送到 GitHub
echo ""
echo "🚀 正在推送到 GitHub..."
git push origin master

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 推送成功！"
    echo "🚀 Railway 将自动重新部署..."
    echo ""
    echo "📱 几分钟后访问您的票多多:"
    echo "   https://railway.app/dashboard"
    echo ""
    echo "   在 Railway 中点击您的项目，查看部署状态"
else
    echo ""
    echo "❌ 推送失败，请检查 GitHub 登录状态"
fi
