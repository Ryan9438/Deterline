# Deterline 房间分类清单（ROOM GUIDE）

> 生成自 game.ios ROOM chunk 全量扫描（2026-08-16）。共 336 个房间。
> 用途：自定义房间时必须按此清单选择**已有房间**改造，**禁止新建房间序号**。

## 分类说明

| 类别 | 定义 | 数量 |
|------|------|------|
| A | 游戏流程中**唯一自带背景视差**的房间 | 1 |
| B | 有背景图（数据启用 或 obj_backgrounder_* 对象），**可注入 GML 实现视差** | 52 |
| C | 无背景、纯 Tile 地板 | 236 |
| D | 全空（intro/credits/测试/战斗房） | 47 |

**选择规则**（用户要求自定义/新建房间时强制遵守）：
1. **禁止新建房间序号**——只能修改已有房间（`set-room-prop`/`set-room-view`/`set-room-bg`/`gml-bg`/Tile 编辑）
2. 用户要求**加背景或视差** → 必须选 **B 类**（如 room_tundra_town 等可滚动长房最佳）
3. 用户要求**纯地板场景** → 选 **C 类**
4. 尺寸注意：320x240 小房视角静止（无滚动），横长房（W>320）才有视差观察空间
5. 提供候选时列出房间号 + 尺寸 + 中文名，供用户挑选

## A 类（1）

| 房间号 | 内部名 | 尺寸 | 视角 | Tile数 | 中文名 |
|------|--------|------|------|-------|--------|
| 230 | room_lastruins_corridor | 2120x240 | 可滚动 | 589 |  (新家 - 电梯)

## B 类（52）

| 房间号 | 内部名 | 尺寸 | 视角 | Tile数 | 中文名 |
|------|--------|------|------|-------|--------|
|   4 | room_area1 | 680x260 | 可滚动 | 20 |  (遗迹 - 起始点)
|   5 | room_area1_2 | 320x420 | 可滚动 | 0 |  (遗迹 - 小花的地方)
|  30 | room_ruins18OLD | 320x240 | 静止 | 64 |  (遗迹 - 有玩具刀的房间)
|  32 | room_torhouse1 | 320x240 | 静止 | 5 |  (托丽尔的家: 入口)
|  33 | room_torhouse2 | 320x240 | 静止 | 5 |  (托丽尔的家: 阅读室)
|  36 | room_asrielroom | 320x240 | 静止 | 0 |  (托丽尔的家: 你的房间)
|  37 | room_kitchen | 320x240 | 静止 | 0 |  (托丽尔的家: 厨房)
|  43 | room_ruinsexit | 320x420 | 可滚动 | 0 |  (托丽尔的地下室: 嘲讽你的小花)
|  65 | room_tundra_iceexit | 600x240 | 可滚动 | 217 |  (雪镇 - 冰洞的入口)
|  66 | room_tundra_poffzone | 560x240 | 可滚动 | 242 |  (雪镇 - 大犬汪)
|  67 | room_tundra_dangerbridge | 1040x240 | 可滚动 | 278 |  (雪镇 - 帕派瑞斯直截了当的攻击谜题)
|  68 | room_tundra_town | 2720x240 | 可滚动 | 1637 |  (雪镇 - 镇子 [SAVE])
|  73 | room_tundra_grillby | 320x240 | 静止 | 0 |  (雪镇 - Grillby's 酒吧)
|  76 | room_tundra_sanshouse | 320x240 | 静止 | 0 |
|  77 | room_tundra_paproom | 320x240 | 静止 | 0 |
|  78 | room_tundra_sansroom | 320x240 | 静止 | 0 |
| 108 | room_water_waterfall3 | 1400x240 | 可滚动 | 2 |  (瀑布 - 宫殿远景)
| 110 | room_water_preundyne | 720x240 | 可滚动 | 480 |  (瀑布 - 桥 [SAVE])
| 111 | room_water_undynebridge | 1940x1240 | 可滚动 | 1894 |  (瀑布 - 桥上躲避安黛因)
| 118 | room_water_undynehouse | 320x240 | 静止 | 0 |
| 120 | room_water_blookhouse | 320x240 | 静止 | 1 |
| 121 | room_water_hapstablook | 320x240 | 静止 | 1 |
| 134 | room_water_undynefinal | 320x740 | 可滚动 | 125 |  (瀑布 - 安黛因竞技场)
| 137 | room_fire1 | 520x240 | 可滚动 | 97 |  (热域 - 入口)
| 138 | room_fire2 | 320x240 | 静止 | 125 |  (热域 - 饮水机)
| 139 | room_fire_prelab | 600x240 | 可滚动 | 296 |  (热域 - 实验室入口 [SAVE])
| 155 | room_fire_savepoint1 | 720x240 | 可滚动 | 180 |  (热域 - 核心景象 [SAVE])
| 167 | room_fire_coreview2 | 720x240 | 可滚动 | 165 |  (热域 - 上层核心景象)
| 179 | room_fire_operatest | 320x380 | 可滚动 | 24 |  (热域 - 剧院舞台)
| 188 | room_fire_precore | 320x560 | 可滚动 | 245 |  (热域 - 核心入口)
| 217 | room_castle_precastle | 1300x240 | 可滚动 | 463 |  (城堡 - 另一个电梯)
| 218 | room_castle_hook | 320x940 | 可滚动 | 254 |  (城堡 - 黑暗的小径)
| 220 | room_asghouse1 | 320x240 | 静止 | 5 |  (新家 - 入口)
| 221 | room_asghouse2 | 320x240 | 静止 | 5 |  (新家 - 阅读室)
| 224 | room_asrielroom_final | 320x240 | 静止 | 0 |  (新家 - 你的房间)
| 225 | room_kitchen_final | 320x240 | 静止 | 0 |  (新家 - 厨房)
| 231 | room_sanscorridor | 1400x240 | 可滚动 | 479 |  (最后的长廊 [SAVE])
| 236 | room_castle_prebarrier | 680x260 | 可滚动 | 44 |  (终点 [SAVE])
| 238 | room_castle_exit | 320x420 | 可滚动 | 0 |
| 240 | room_castle_trueexit | 320x420 | 可滚动 | 0 |
| 241 | room_outsideworld | 320x240 | 静止 | 0 |  (外面)
| 279 | room_end_highway | 640x240 | 可滚动 | 146 |
| 285 | room_end_myroom | 320x240 | 静止 | 77 |
| 306 | room_battle | 640x480 | 可滚动 | 0 |
| 307 | room_floweybattle | 640x480 | 可滚动 | 0 |
| 308 | room_fastbattle | 640x480 | 可滚动 | 0 |
| 309 | room_storybattle | 640x480 | 可滚动 | 0 |
| 313 | room_shop3 | 320x240 | 静止 | 0 |
| 314 | room_shop4 | 320x240 | 静止 | 0 |
| 315 | room_shop5 | 320x240 | 静止 | 0 |
| 319 | room_flowey_endchoice | 640x480 | 可滚动 | 0 |
| 328 | room_friendtest | 640x480 | 可滚动 | 0 |

## C 类（236）

| 房间号 | 内部名 | 尺寸 | 视角 | Tile数 | 中文名 |
|------|--------|------|------|-------|--------|
|   6 | room_ruins1 | 320x480 | 可滚动 | 368 |  (遗迹 - 入口 [SAVE])
|   7 | room_ruins2 | 320x240 | 静止 | 171 |  (遗迹 - 托丽尔踩砖谜题)
|   8 | room_ruins3 | 740x240 | 可滚动 | 454 |  (遗迹 - 开关谜题)
|   9 | room_ruins4 | 320x240 | 静止 | 160 |  (遗迹 - 人偶房间)
|  10 | room_ruins5 | 1200x240 | 可滚动 | 648 |  (遗迹 - 尖刺谜题)
|  11 | room_ruins6 | 2500x240 | 可滚动 | 1319 |  (遗迹 - 长走廊)
|  12 | room_ruins7 | 320x480 | 可滚动 | 357 |  (遗迹 - 落叶堆 [SAVE])
|  13 | room_ruins7A | 320x240 | 静止 | 150 |  (遗迹 - 糖果柱)
|  14 | room_ruins8 | 320x640 | 可滚动 | 266 |  (遗迹 - 强制掉落陷阱)
|  15 | room_ruins9 | 480x240 | 可滚动 | 261 |  (遗迹 - 第一个推石头谜题)
|  16 | room_ruins10 | 580x760 | 可滚动 | 652 |  (遗迹 - 陷阱门走廊谜题)
|  17 | room_ruins11 | 560x240 | 可滚动 | 310 |  (遗迹 - 会说话的岩石)
|  18 | room_ruins12A | 320x240 | 静止 | 132 |  (遗迹 - 老鼠洞 [SAVE])
|  19 | room_ruins12 | 320x240 | 静止 | 173 |  (遗迹 - 小幽灵 Napstablook)
|  20 | room_ruins12B | 320x240 | 静止 | 117 |  (遗迹 - 蜘蛛烘焙义卖)
|  21 | room_ruins13 | 640x300 | 可滚动 | 341 |  (遗迹 - 两只青蛙)
|  22 | room_ruins14 | 640x720 | 可滚动 | 623 |  (遗迹 - 藏在陷阱们谜题下的开关)
|  23 | room_ruins15A | 400x440 | 可滚动 | 274 |  (遗迹 - 三个柱子房间 1)
|  24 | room_ruins15B | 400x440 | 可滚动 | 264 |  (遗迹 - 三个柱子房间 2)
|  25 | room_ruins15C | 400x440 | 可滚动 | 265 |  (遗迹 - 三个柱子房间 3)
|  26 | room_ruins15D | 400x440 | 可滚动 | 275 |  (遗迹 - 三个柱子房间 4)
|  27 | room_ruins15E | 320x240 | 静止 | 152 |  (遗迹 - 柱子房间的坑)
|  28 | room_ruins16 | 600x400 | 可滚动 | 507 |  (遗迹 - 三条路的分叉)
|  29 | room_ruins17 | 320x640 | 可滚动 | 97 |  (遗迹 - 说托丽尔闲话的青蛙)
|  31 | room_ruins19 | 320x540 | 可滚动 | 437 |  (遗迹 - 家 [SAVE])
|  34 | room_torhouse3 | 800x240 | 可滚动 | 92 |  (托丽尔的家: 走廊)
|  35 | room_torielroom | 320x240 | 静止 | 1 |  (托丽尔的家: 托丽尔的房间)
|  38 | room_basement1 | 500x240 | 可滚动 | 179 |  (托丽尔的地下室 1)
|  39 | room_basement2 | 500x240 | 可滚动 | 185 |  (托丽尔的地下室 2)
|  40 | room_basement3 | 320x240 | 静止 | 102 |  (托丽尔的地下室 3)
|  41 | room_basement4 | 320x240 | 静止 | 115 |  (托丽尔的地下室: 托丽尔的 Boss 战)
|  42 | room_basement5 | 320x1620 | 可滚动 | 312 |  (托丽尔的地下室: 即将遇到小花的走廊)
|  44 | room_tundra1 | 440x240 | 可滚动 | 238 |  (雪镇 - 遗迹出口)
|  45 | room_tundra2 | 2720x240 | 可滚动 | 1203 |  (雪镇 - 黑暗的森林小径)
|  46 | room_tundra3 | 400x240 | 可滚动 | 344 |  (雪镇 - 盒子路 [SAVE])
|  47 | room_tundra3A | 320x240 | 静止 | 256 |  (雪镇 - 钓鱼竿)
|  48 | room_tundra4 | 560x240 | 可滚动 | 482 |  (雪镇 - 帕派瑞斯的哨站)
|  49 | room_tundra5 | 460x240 | 可滚动 | 200 |  (雪镇 - 遁狗)
|  50 | room_tundra6 | 620x240 | 可滚动 | 406 |  (雪镇 - 指路标)
|  51 | room_tundra6A | 320x240 | 静止 | 104 |  (雪镇 - 雪人)
|  52 | room_tundra7 | 320x240 | 静止 | 219 |  (雪镇 - 电击迷宫)
|  53 | room_tundra8 | 760x580 | 可滚动 | 1471 |  (雪镇 - 推雪球游戏)
|  54 | room_tundra8A | 320x240 | 静止 | 193 |  (雪镇 - 两只狗守卫的房子)
|  55 | room_tundra9 | 320x240 | 静止 | 340 |  (雪镇 - 怪物小孩的纵横谜题)
|  56 | room_tundra_spaghetti | 320x240 | 静止 | 245 |  (雪镇 - 意大利面 [SAVE])
|  57 | room_tundra_snowpuzz | 620x580 | 可滚动 | 1078 |  (雪镇 - 狗夫妇)
|  58 | room_tundra_xoxosmall | 500x240 | 可滚动 | 448 |  (雪镇 - XO 谜题 1)
|  59 | room_tundra_xoxopuzz | 820x240 | 可滚动 | 467 |  (雪镇 - XO 谜题 2)
|  60 | room_tundra_randoblock | 320x240 | 静止 | 170 |  (雪镇 - 踩砖谜题)
|  61 | room_tundra_lesserdog | 560x240 | 可滚动 | 265 |  (雪镇 - 狗屋 [SAVE])
|  62 | room_tundra_icehole | 320x240 | 静止 | 120 |  (雪镇 - 帕派瑞斯和衫斯的雪雕)
|  63 | room_tundra_iceentrance | 940x240 | 可滚动 | 723 |  (雪镇 - 冰面滑行的 XO 谜题)
|  64 | room_tundra_iceexit_new | 600x240 | 可滚动 | 415 |  (雪镇 - 会瞬移的衫斯)
|  69 | room_tundra_town2 | 800x240 | 可滚动 | 585 |  (雪镇 - 冰狼)
|  70 | room_tundra_dock | 320x240 | 静止 | 235 |  (雪镇 - 船夫(妇))
|  71 | room_tundra_inn | 320x240 | 静止 | 87 |  (雪镇 - 旅店)
|  72 | room_tundra_inn_2f | 320x240 | 静止 | 110 |
|  74 | room_tundra_library | 320x240 | 静止 | 101 |  (雪镇 - 图书馆)
|  75 | room_tundra_garage | 320x240 | 静止 | 62 |
|  79 | room_tundra_sansroom_dark | 1000x580 | 可滚动 | 1 |
|  80 | room_tundra_sansbasement | 320x240 | 静止 | 67 |
|  81 | room_fogroom | 900x240 | 可滚动 | 508 |  (雪镇 - 帕派瑞斯的战斗)
|  82 | room_water1 | 640x240 | 可滚动 | 426 |  (瀑布 - 入口)
|  83 | room_water2 | 320x240 | 静止 | 203 |  (瀑布 - 检查点 [SAVE])
|  84 | room_water3 | 580x540 | 可滚动 | 394 |  (瀑布 - 坠落的石头)
|  85 | room_water3A | 320x240 | 静止 | 98 |
|  86 | room_water4 | 560x400 | 可滚动 | 373 |  (瀑布 - 门厅(?) [SAVE])
|  87 | room_water_bridgepuzz1 | 520x240 | 可滚动 | 283 |  (瀑布 - 桥花)
|  88 | room_water5 | 500x500 | 可滚动 | 602 |  (瀑布 - 垂直的桥花(?))
|  89 | room_water5A | 320x240 | 静止 | 124 |
|  90 | room_water6 | 740x380 | 可滚动 | 325 |  (瀑布 - 望远镜)
|  91 | room_water7 | 1100x340 | 可滚动 | 251 |  (瀑布 - 船板)
|  92 | room_water8 | 2100x300 | 可滚动 | 855 |  (瀑布 - 安黛因躲避 1)
|  93 | room_water9 | 860x240 | 可滚动 | 226 |  (瀑布 - 躲避安黛因之后的草丛)
|  94 | room_water_savepoint1 | 320x240 | 静止 | 140 |  (瀑布 - 水晶奶酪 [SAVE])
|  95 | room_water11 | 660x340 | 可滚动 | 479 |  (瀑布 - 衫斯的望远镜)
|  96 | room_water_nicecream | 320x440 | 可滚动 | 213 |  (瀑布 - 好棒冰)
|  97 | room_water12 | 1280x820 | 可滚动 | 1370 |  (瀑布 - 分岔路(?))
|  98 | room_water_shoe | 320x240 | 静止 | 49 |  (瀑布 - 芭蕾舞鞋)
|  99 | room_water_bird | 320x240 | 静止 | 131 |  (瀑布 - 带你过河的鸟)
| 100 | room_water_onionsan | 1220x240 | 可滚动 | 418 |  (瀑布 - 洋葱桑)
| 101 | room_water14 | 740x240 | 可滚动 | 361 |  (瀑布 - 神器)
| 102 | room_water_piano | 320x240 | 静止 | 142 |  (瀑布 - 钢琴)
| 103 | room_water_dogroom | 320x240 | 静止 | 105 |  (瀑布 - 传说神器)
| 104 | room_water_statue | 320x240 | 静止 | 146 |  (瀑布 - 淋雨的雕像)
| 105 | room_water_prewaterfall | 340x240 | 可滚动 | 154 |  (瀑布 - 雨伞)
| 106 | room_water_waterfall | 1640x240 | 可滚动 | 619 |  (瀑布 - 下雨的小路 1)
| 107 | room_water_waterfall2 | 320x1040 | 可滚动 | 334 |  (瀑布 - 小雨的小路 2)
| 109 | room_water_waterfall4 | 520x240 | 可滚动 | 177 |  (瀑布 - 雨伞归还处)
| 112 | room_water_undynebridgeend | 820x1140 | 可滚动 | 111 |  (瀑布 - 桥 坠落)
| 113 | room_water_trashzone1 | 820x240 | 可滚动 | 434 |  (瀑布 - 垃圾场 花床)
| 114 | room_water_trashsavepoint | 320x240 | 静止 | 177 |  (瀑布 - 垃圾场 [SAVE])
| 115 | room_water_trashzone2 | 320x940 | 可滚动 | 474 |  (瀑布 - 大表哥(发怒人偶)的复仇)
| 116 | room_water_friendlyhub | 620x240 | 可滚动 | 549 |  (瀑布 - 宁静地带 [SAVE])
| 117 | room_water_undyneyard | 320x240 | 静止 | 121 |  (瀑布 - 安黛因房子入口)
| 119 | room_water_blookyard | 320x240 | 静止 | 154 |  (瀑布 - 两个幽灵的房子)
| 122 | room_water_farm | 760x240 | 可滚动 | 493 |
| 123 | room_water_prebird | 620x240 | 可滚动 | 63 |
| 124 | room_water_shop | 320x240 | 静止 | 166 |  (瀑布 - 乌龟 Gerson 的商店)
| 125 | room_water_dock | 320x240 | 静止 | 152 |  (瀑布 - 渔夫(妇))
| 126 | room_water15 | 1020x240 | 可滚动 | 344 |  (瀑布 - 两个瀑布)
| 127 | room_water16 | 620x640 | 可滚动 | 162 |  (瀑布 - 发光蘑菇迷宫)
| 128 | room_water_temvillage | 660x300 | 可滚动 | 274 |  (瀑布 - 提米村 [SAVE])
| 129 | room_water17 | 640x540 | 可滚动 | 222 |  (瀑布 - 黑暗迷宫)
| 130 | room_water18 | 1020x240 | 可滚动 | 237 |  (瀑布 - "在你后面")
| 131 | room_water19 | 320x640 | 可滚动 | 321 |  (瀑布 - 更多的回音花)
| 132 | room_water20 | 620x240 | 可滚动 | 217 |  (瀑布 - 洞穴 桥)
| 133 | room_water21 | 320x240 | 静止 | 135 |  (瀑布 - 洞穴 出口)
| 135 | room_water_undynefinal2 | 320x480 | 可滚动 | 183 |  (瀑布 - 安黛因竞技场 + 1)
| 136 | room_water_undynefinal3 | 720x240 | 可滚动 | 146 |  (瀑布 - 热域欢迎词)
| 140 | room_fire_dock | 320x240 | 静止 | 127 |  (热域 - 船夫(妇))
| 141 | room_fire_lab1 | 1100x240 | 可滚动 | 559 |  (热域 - 实验室)
| 142 | room_fire_lab2 | 860x240 | 可滚动 | 584 |  (热域 - 实验室二楼)
| 143 | room_fire3 | 480x340 | 可滚动 | 256 |  (热域 - 实验室出口)
| 144 | room_fire5 | 320x1640 | 可滚动 | 611 |  (热域 - 传送带 1)
| 145 | room_fire6 | 860x440 | 可滚动 | 605 |  (热域 - 岩浆房 [SAVE])
| 146 | room_fire6A | 620x240 | 可滚动 | 218 |  (热域 - 烧焦的平底锅)
| 147 | room_fire_lasers1 | 1160x240 | 可滚动 | 953 |  (热域 - 激光 1)
| 148 | room_fire7 | 520x560 | 可滚动 | 635 |  (热域 - 谜题 门 1)
| 149 | room_fire8 | 360x240 | 可滚动 | 188 |  (热域 - 左边谜题的入口)
| 150 | room_fire_shootguy_2 | 320x240 | 静止 | 59 |  (热域 - 左边的谜题)
| 151 | room_fire9 | 320x240 | 静止 | 166 |  (热域 - 右边谜题的入口)
| 152 | room_fire_shootguy_1 | 320x240 | 静止 | 51 |  (热域 - 右边的谜题)
| 153 | room_fire_turn | 800x240 | 可滚动 | 201 |  (热域 - 通往击毁敌船谜题的桥)
| 154 | room_fire_cookingshow | 640x480 | 可滚动 | 414 |  (热域 - 厨房)
| 156 | room_fire_elevator_r1 | 320x240 | 静止 | 104 |  (热域 - 电梯 R1)
| 157 | room_fire_elevator_r2 | 320x240 | 静止 | 85 |  (热域 - 电梯 R2)
| 158 | room_fire_hotdog | 320x240 | 静止 | 130 |  (热域 - 热狗站)
| 159 | room_fire_walkandbranch | 820x240 | 可滚动 | 236 |  (热域 - 美术俱乐部入口)
| 160 | room_fire_sorry | 320x240 | 静止 | 106 |  (热域 - 美术俱乐部（So Sorry）)
| 161 | room_fire_apron | 520x240 | 可滚动 | 140 |  (热域 - 染色围裙)
| 162 | room_fire10 | 840x240 | 可滚动 | 325 |  (热域 - 传送带开关谜题)
| 163 | room_fire_rpuzzle | 620x540 | 可滚动 | 528 |  (热域 - 击毁敌船谜题)
| 164 | room_fire_mewmew2 | 520x240 | 可滚动 | 145 |  (热域 - 蠢念头区域 [SAVE])
| 165 | room_fire_boysnightout | 620x440 | 可滚动 | 324 |  (热域 - 守卫好基友)
| 166 | room_fire_newsreport | 980x660 | 可滚动 | 737 |  (热域 - 镁塔顿的新闻报道)
| 168 | room_fire_elevator_l2 | 320x240 | 静止 | 106 |  (热域 - 电梯 L2)
| 169 | room_fire_elevator_l3 | 320x240 | 静止 | 74 |  (热域 - 电梯 L3)
| 170 | room_fire_spidershop | 480x240 | 可滚动 | 146 |  (热域 - 蜘蛛烘焙义卖)
| 171 | room_fire_walkandbranch2 | 900x660 | 可滚动 | 362 |  (热域 - F3 谜题 门)
| 172 | room_fire_conveyorlaser | 1000x440 | 可滚动 | 379 |  (热域 - F3 南边谜题入口)
| 173 | room_fire_shootguy_3 | 320x240 | 静止 | 59 |  (热域 - F3 南边谜题)
| 174 | room_fire_preshootguy4 | 320x320 | 可滚动 | 83 |  (热域 - F3 北边谜题入口)
| 175 | room_fire_shootguy_4 | 320x240 | 静止 | 54 |  (热域 - F3 北边谜题)
| 176 | room_fire_savepoint2 | 500x240 | 可滚动 | 153 |  (热域 - 蜘蛛 入口 [SAVE])
| 177 | room_fire_spider | 1020x240 | 可滚动 | 124 |  (热域 - 蜘蛛 房间)
| 178 | room_fire_pacing | 320x240 | 静止 | 88 |  (热域 - 镁塔顿海报)
| 180 | room_fire_multitile | 1360x240 | 可滚动 | 223 |  (热域 - 踩砖谜题 2)
| 181 | room_fire_hotelfront_1 | 520x240 | 可滚动 | 177 |  (热域 - 好棒冰站 2)
| 182 | room_fire_hotelfront_2 | 480x400 | 可滚动 | 443 |  (热域 - 酒店入口)
| 183 | room_fire_hotellobby | 520x600 | 可滚动 | 371 |  (热域 - 酒店大厅 [SAVE])
| 184 | room_fire_restaurant | 1020x320 | 可滚动 | 514 |  (热域 - 酒店餐馆)
| 185 | room_fire_hoteldoors | 820x240 | 可滚动 | 97 |  (热域 - 酒店走廊)
| 186 | room_fire_hotelbed | 320x240 | 静止 | 116 |  (热域 - 酒店旁的小巷)
| 187 | room_fire_elevator_r3 | 320x240 | 静止 | 65 |  (热域 - 电梯 R3)
| 189 | room_fire_core1 | 320x300 | 可滚动 | 319 |  (热域 - 核心电梯)
| 190 | room_fire_core2 | 320x340 | 可滚动 | 26 |  (热域 - 核心 洞)
| 191 | room_fire_core3 | 320x420 | 可滚动 | 188 |  (热域 - 核心 北边的电梯)
| 192 | room_fire_core4 | 680x240 | 可滚动 | 190 |  (热域 - 核心 顺序错误的激光)
| 193 | room_fire_core5 | 320x240 | 静止 | 159 |  (热域 - 核心 十字路口)
| 194 | room_fire_core_freebattle | 320x240 | 静止 | 123 |  (热域 - 核心 死路)
| 195 | room_fire_core_laserfun | 1200x240 | 可滚动 | 234 |  (热域 - 核心 能量激光谜题)
| 196 | room_fire_core_branch | 320x240 | 静止 | 227 |  (热域 - 核心 分支 [SAVE])
| 197 | room_fire_core_bottomleft | 320x240 | 静止 | 129 |  (热域 - 核心 冰块储存(?))
| 198 | room_fire_core_left | 320x240 | 静止 | 110 |  (热域 - 核心 西边谜题入口)
| 199 | room_fire_core_topleft | 320x240 | 静止 | 252 |  (热域 - 核心 西边谜题入口 + 1)
| 200 | room_fire_core_top | 320x240 | 静止 | 272 |  (热域 - 核心 西边谜题入口 + 2)
| 201 | room_fire_core_topright | 320x240 | 静止 | 212 |  (热域 - 核心 南边有 100G 的垃圾桶)
| 202 | room_fire_core_right | 320x240 | 静止 | 186 |  (热域 - 核心 尽头 - 3)
| 203 | room_fire_core_bottomright | 320x240 | 静止 | 70 |  (热域 - 核心 尽头 - 4)
| 204 | room_fire_core_center | 320x240 | 静止 | 129 |  (热域 - 核心 迷路)
| 205 | room_fire_shootguy_5 | 320x240 | 静止 | 61 |  (热域 - 核心 西边的谜题)
| 206 | room_fire_core_treasureleft | 320x240 | 静止 | 101 |  (热域 - 核心 有魅力汉堡的垃圾桶)
| 207 | room_fire_core_treasureright | 320x240 | 静止 | 101 |  (热域 - 核心 有 100G 的垃圾桶)
| 208 | room_fire_core_warrior | 780x240 | 可滚动 | 148 |  (热域 - 核心 终极怪物桥)
| 209 | room_fire_core_bridge | 620x240 | 可滚动 | 188 |  (热域 - 核心 尽头 - 1)
| 210 | room_fire_core_premett | 320x240 | 静止 | 152 |  (热域 - 核心 尽头 [SAVE])
| 211 | room_fire_core_metttest | 320x1000 | 可滚动 | 350 |  (热域 - 核心 镁塔顿的房间)
| 212 | room_fire_core_final | 1220x240 | 可滚动 | 385 |  (热域 - 核心 最终电梯的入口)
| 213 | room_fire_elevator | 320x240 | 静止 | 42 |
| 214 | room_fire_elevator_l1 | 320x240 | 静止 | 68 |  (热域 - 电梯 L1)
| 215 | room_fire_finalelevator | 320x240 | 静止 | 42 |  (热域 - 核心 电梯入口)
| 216 | room_castle_elevatorout | 520x240 | 可滚动 | 319 |  (城堡 - 电梯 [SAVE])
| 219 | room_castle_front | 320x540 | 可滚动 | 529 |  (新家 [SAVE])
| 222 | room_asghouse3 | 800x240 | 可滚动 | 93 |  (新家 - 走廊)
| 223 | room_asgoreroom | 320x240 | 静止 | 1 |  (新家 - 艾斯戈尔的房间)
| 226 | room_basement1_final | 500x240 | 可滚动 | 358 |  (新家 - 地下室 1)
| 227 | room_basement2_final | 500x240 | 可滚动 | 321 |  (新家 - 地下室 2)
| 228 | room_basement3_final | 320x240 | 静止 | 198 |  (新家 - 地下室 3)
| 229 | room_basement4_final | 320x240 | 静止 | 211 |  (新家 - 地下室 4)
| 232 | room_castle_finalshoehorn | 820x540 | 可滚动 | 543 |  (王座 入口 [SAVE])
| 233 | room_castle_coffins1 | 320x540 | 可滚动 | 81 |  (王座 入口 - 下楼)
| 234 | room_castle_coffins2 | 520x240 | 可滚动 | 177 |  (王座 入口 - 棺材)
| 235 | room_castle_throneroom | 320x600 | 可滚动 | 485 |  (王座 房间 [SAVE])
| 242 | room_fire_labelevator | 320x240 | 静止 | 42 |  (实验室电梯)
| 243 | room_truelab_elevatorinside | 320x240 | 静止 | 30 |  (真实验室 - 电梯)
| 244 | room_truelab_elevator | 320x240 | 静止 | 50 |  (真实验室 - 电梯入口)
| 245 | room_truelab_hall1 | 840x240 | 可滚动 | 104 |  (真实验室 - 南边的走廊)
| 246 | room_truelab_hub | 500x620 | 可滚动 | 146 |  (真实验室 [SAVE])
| 247 | room_truelab_hall2 | 420x240 | 可滚动 | 48 |  (真实验室 - 西边的走廊 1)
| 248 | room_truelab_operatingroom | 580x240 | 可滚动 | 121 |  (真实验室 - 西边的坠落(?))
| 249 | room_truelab_redlever | 320x240 | 静止 | 31 |  (真实验室 - 西边的红色钥匙孔)
| 250 | room_truelab_prebed | 600x240 | 可滚动 | 63 |  (真实验室 - 北边的走廊 1)
| 251 | room_truelab_bedroom | 540x540 | 可滚动 | 305 |  (真实验室 - 卧室 [SAVE])
| 252 | room_truelab_mirror | 1000x240 | 可滚动 | 298 |  (真实验室 - 南北边的走廊)
| 253 | room_truelab_bluelever | 320x240 | 静止 | 31 |  (真实验室 - 南北边的蓝色钥匙孔)
| 254 | room_truelab_hall3 | 1160x240 | 可滚动 | 149 |  (真实验室 - 北边的走廊 2)
| 255 | room_truelab_shower | 320x240 | 静止 | 27 |  (真实验室 - 绿色钥匙)
| 256 | room_truelab_determination | 460x240 | 可滚动 | 63 |  (真实验室 - 西北边的决心提取器)
| 257 | room_truelab_tv | 320x240 | 静止 | 75 |  (真实验室 - 黄色钥匙孔 + 电视)
| 258 | room_truelab_cooler | 720x240 | 可滚动 | 187 |  (真实验室 - 西北边的冰箱)
| 259 | room_truelab_greenlever | 320x240 | 静止 | 31 |  (真实验室 - 绿色钥匙孔)
| 260 | room_truelab_fan | 580x240 | 可滚动 | 33 |  (真实验室 - 风扇)
| 261 | room_truelab_castle_elevator | 320x240 | 静止 | 40 |  (真实验室 - 电梯 2)
| 262 | room_truelab_prepower | 580x240 | 可滚动 | 63 |  (真实验室 - 动力室走廊)
| 263 | room_truelab_power | 320x420 | 可滚动 | 130 |  (真实验室 - 动力室)
| 265 | room_icecave1 | 320x580 | 可滚动 | 111 |  (雪镇 - 冰洞 1)
| 266 | room_ice_dog | 320x240 | 静止 | 97 |
| 268 | room_water_fakehallway | 320x240 | 静止 | 112 |
| 269 | room_mysteryman | 320x240 | 静止 | 40 |
| 273 | room_water13 | 320x640 | 可滚动 | 252 |
| 280 | room_end_beach | 320x240 | 静止 | 65 |
| 281 | room_end_metta | 320x240 | 静止 | 238 |
| 282 | room_end_school | 320x480 | 可滚动 | 330 |
| 289 | room_controltest | 320x240 | 静止 | 18 |
| 296 | room_fire4 | 1420x540 | 可滚动 | 299 |
| 297 | room_fire10_old | 1320x240 | 可滚动 | 260 |
| 298 | room_fire10A_old | 1220x240 | 可滚动 | 300 |
| 299 | room_tundra_placeholder | 320x800 | 可滚动 | 566 |
| 300 | room_ruins12B_old | 320x240 | 静止 | 81 |
| 301 | room_tundra_rollsnow | 320x240 | 静止 | 65 |
| 302 | room_water7_older | 800x340 | 可滚动 | 208 |
| 303 | room_meetundyne_old | 560x240 | 可滚动 | 222 |
| 304 | room_water_mushroom | 320x240 | 静止 | 81 |
| 316 | room_riverman_transition | 660x240 | 可滚动 | 166 |
| 335 | room_dogshrine | 320x240 | 静止 | 136 |

## D 类（47）

| 房间号 | 内部名 | 尺寸 | 视角 | Tile数 | 中文名 |
|------|--------|------|------|-------|--------|
|   0 | room_start | 640x480 | 可滚动 | 0 |
|   1 | room_introstory | 320x240 | 静止 | 0 |
|   2 | room_introimage | 320x240 | 静止 | 0 |
|   3 | room_intromenu | 320x240 | 静止 | 0 |
| 237 | room_castle_barrier | 320x240 | 静止 | 0 |  (结界)
| 239 | room_undertale_end | 320x240 | 静止 | 0 |
| 264 | room_gaster | 320x240 | 静止 | 0 |
| 267 | room2 | 640x480 | 可滚动 | 0 |
| 270 | room_soundtest | 640x480 | 可滚动 | 0 |
| 271 | TESTROOM | 640x480 | 可滚动 | 0 |
| 272 | room_water_redacted | 320x240 | 静止 | 0 |
| 274 | room_overworld | 1280x640 | 可滚动 | 0 |
| 275 | room_overworld3 | 640x480 | 可滚动 | 0 |
| 276 | bullettest | 640x480 | 可滚动 | 0 |
| 277 | room_water16A | 320x240 | 静止 | 0 |
| 278 | room_end_castroll | 640x480 | 可滚动 | 0 |
| 283 | room_end_mtebott | 640x480 | 可滚动 | 0 |
| 284 | room_creditsdodger | 640x480 | 可滚动 | 0 |
| 286 | room_end_theend | 640x480 | 可滚动 | 0 |
| 287 | room_spritecheck | 640x480 | 可滚动 | 0 |
| 288 | room_settings | 320x240 | 静止 | 0 |
| 290 | room_f_start | 320x240 | 静止 | 0 |
| 291 | room_f_intro | 320x240 | 静止 | 0 |
| 292 | room_f_menu | 320x240 | 静止 | 0 |
| 293 | room_f_room | 320x520 | 可滚动 | 0 |
| 294 | room_floweyx | 640x480 | 可滚动 | 0 |
| 295 | room_f_phrase | 640x480 | 可滚动 | 0 |
| 305 | room_monsteralign_test | 640x480 | 可滚动 | 0 |
| 310 | room_gameover | 640x480 | 可滚动 | 0 |
| 311 | room_shop1 | 320x240 | 静止 | 0 |
| 312 | room_shop2 | 320x240 | 静止 | 0 |
| 317 | room_papdate | 640x480 | 可滚动 | 0 |
| 318 | room_adate | 640x480 | 可滚动 | 0 |
| 320 | room_flowey_regret | 320x240 | 静止 | 0 |
| 321 | room_empty | 320x240 | 静止 | 0 |
| 322 | room_emptywhite | 640x480 | 可滚动 | 0 |
| 323 | room_emptyblack | 640x480 | 可滚动 | 0 |
| 324 | room_nothingness | 320x240 | 静止 | 0 |
| 325 | room_undertale | 320x240 | 静止 | 0 |
| 326 | room_of_dog | 320x240 | 静止 | 0 |
| 327 | room_quizholder | 640x480 | 可滚动 | 0 |
| 329 | room_bringitinguys | 640x480 | 可滚动 | 0 |
| 330 | room_asrielappears | 640x480 | 可滚动 | 0 |
| 331 | room_goodbyeasriel | 320x240 | 静止 | 0 |  (艾斯瑞尔/小羊的房间)
| 332 | room_asrielmemory | 640x480 | 可滚动 | 0 |
| 333 | room_asrieltest | 640x480 | 可滚动 | 0 |
| 334 | room_afinaltest | 640x480 | 可滚动 | 0 |
