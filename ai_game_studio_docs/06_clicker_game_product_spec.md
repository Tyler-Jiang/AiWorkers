# AI Game Studio - 第一版点击成长小游戏需求文档

## 1. 项目目标
作为多角色 AI 游戏团队的第一个交付项目，第一版固定为一个点击成长类 Web 小游戏。

## 2. 核心玩法
玩家点击主按钮获得资源。资源可用于升级点击效率。升级后每次点击收益提升，形成最小成长循环。

## 3. 最低功能范围
### 必须有
- 点击主按钮
- 资源总数显示
- 升级按钮
- 升级价格显示
- 升级后点击收益提升
- 简单视觉反馈
- 基础深色界面

## 4. 游戏状态
- resource_count
- click_power
- level
- next_upgrade_cost

## 5. 基础规则
初始值：
- resource_count = 0
- click_power = 1
- level = 1
- next_upgrade_cost = 10

点击：
- resource_count += click_power

升级：
- resource_count -= next_upgrade_cost
- level += 1
- click_power += 1
- next_upgrade_cost = floor(next_upgrade_cost * 1.5)

## 6. 验收标准
1. 点击后资源数正确增加
2. 升级按钮在资源不足时不可用或有明确提示
3. 升级后数值变化正确
4. UI 基本清晰
5. 团队最终能交付可运行小游戏
