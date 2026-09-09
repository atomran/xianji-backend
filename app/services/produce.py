"""21类蔬果冷藏规则 — 从 backend/produce.py 零改动迁移。"""
from datetime import date, timedelta

SOURCE_UMD = 'https://www.extension.umd.edu/resource/storing-garden-fruits-and-vegetables'
SOURCE_MAINE = 'https://extension.umaine.edu/food-health/2025/05/29/storing-and-washing-fresh-fruits-and-vegetables/'
SOURCE_KEEPER = 'https://extension.uga.edu/content/dam/extension-county-offices/gwinnett-county/facs/Food_Keeper_Guide.pdf'

RULES = [
    dict(key='apple', name='苹果', days=14, range='约 3 周', aliases=['苹果'], source=SOURCE_KEEPER, note='完整果实冷藏；提醒提前至 14 天，拍摄前的存放时间未知。'),
    dict(key='grapes', name='葡萄 / 提子', days=7, range='约 1 周', aliases=['葡萄', '提子'], source=SOURCE_KEEPER, note='完整果实，去除受损颗粒，保持干爽。'),
    dict(key='citrus', name='橙 / 橘 / 柚 / 柠檬', days=7, range='1–2 周', aliases=['橙', '橘', '桔', '柚', '柠檬'], source=SOURCE_KEEPER, note='完整果实，冷藏，避免积水。'),
    dict(key='kiwi', name='成熟猕猴桃', days=3, range='3–4 天', aliases=['猕猴桃', '奇异果'], source=SOURCE_KEEPER, note='适用于成熟后冷藏的完整果实。'),
    dict(key='avocado', name='成熟牛油果', days=3, range='3–4 天', aliases=['牛油果', '鳄梨'], source=SOURCE_KEEPER, note='适用于成熟后冷藏的完整果实。'),
    dict(key='banana', name='成熟香蕉', days=2, range='约 2 天', aliases=['香蕉'], source=SOURCE_KEEPER, note='成熟后才冷藏；果皮变黑不等于本系统能判断果肉状态。'),
    dict(key='mango', name='芒果 / 木瓜', days=7, range='约 1 周', aliases=['芒果', '木瓜'], source=SOURCE_KEEPER, note='适用于成熟、完整果实冷藏。'),
    dict(key='leafy', name='叶菜 / 菠菜 / 小青菜', days=2, range='2–4 天', aliases=['菠菜', '青菜', '小白菜', '油麦菜', '生菜', '芥蓝', '空心菜', '叶菜'], source=SOURCE_UMD, note='未切、未清洗，保持干爽并尽快冷藏。'),
    dict(key='berries', name='草莓 / 蓝莓等浆果', days=2, range='2–3 天', aliases=['草莓', '蓝莓', '覆盆子', '树莓', '黑莓'], source=SOURCE_UMD, note='去除受损果，未清洗、干燥冷藏。'),
    dict(key='brassica', name='西兰花 / 花菜 / 卷心菜', days=3, range='3–6 天', aliases=['西兰花', '花菜', '菜花', '卷心菜', '包菜', '甘蓝'], source=SOURCE_UMD, note='完整未切，装入透气袋冷藏。'),
    dict(key='roots', name='胡萝卜 / 萝卜等根菜', days=7, range='7–14 天', aliases=['胡萝卜', '白萝卜', '红萝卜', '甜菜', '萝卜'], source=SOURCE_UMD, note='去除叶部，保持干爽，放入蔬果抽屉。'),
    dict(key='ripe_fruit', name='成熟的桃 / 梨 / 油桃', days=5, range='5 天', aliases=['桃', '梨', '油桃'], source=SOURCE_UMD, note='适用于已成熟后冷藏的完整果实。'),
    dict(key='stone_fruit', name='樱桃 / 李子 / 杏', days=7, range='7 天', aliases=['樱桃', '车厘子', '李子', '杏'], source=SOURCE_UMD, note='完整果实，透气袋冷藏。'),
    dict(key='pepper', name='甜椒 / 彩椒', days=5, range='最多 5 天', aliases=['甜椒', '彩椒', '青椒', '红椒'], source=SOURCE_UMD, note='保持完整、干爽，冷藏。'),
    dict(key='cucumber', name='黄瓜', days=5, range='最多 7 天', aliases=['黄瓜', '青瓜'], source=SOURCE_MAINE, note='提醒提前至 5 天；保持干爽，不与苹果或番茄混放。'),
    dict(key='beans', name='四季豆 / 豆角', days=3, range='最多 3 天', aliases=['四季豆', '豆角', '扁豆', '豇豆'], source=SOURCE_MAINE, note='不预洗，装袋冷藏。'),
    dict(key='corn', name='鲜玉米', days=1, range='1–2 天', aliases=['玉米'], source=SOURCE_MAINE, note='尽早食用，带外皮装袋冷藏。'),
    dict(key='eggplant', name='茄子', days=1, range='1–2 天', aliases=['茄子'], source=SOURCE_MAINE, note='优先尽快食用；需要存放时短期冷藏。'),
    dict(key='herbs', name='香菜 / 新鲜香草', days=2, range='2–3 天', aliases=['香菜', '罗勒', '薄荷', '香草'], source=SOURCE_MAINE, note='防止叶片失水，避免积水。'),
    dict(key='peas', name='豌豆 / 荷兰豆', days=2, range='2–3 天', aliases=['豌豆', '荷兰豆'], source=SOURCE_MAINE, note='未清洗，透气袋冷藏。'),
    dict(key='zucchini', name='西葫芦', days=2, range='2–3 天', aliases=['西葫芦', '角瓜'], source=SOURCE_MAINE, note='表面干爽，装袋冷藏。'),
    dict(key='cut', name='已切 / 去皮的蔬果', days=3, range='3–4 天', aliases=[], source=SOURCE_MAINE, note='适用于及时冷藏、清洁密封容器；以切开时间更早者为起点。'),
]
RULE_MAP = {r['key']: r for r in RULES}

def find_rule(name, key=None, condition='whole'):
    if condition == 'cut':
        return RULE_MAP['cut']
    if key in RULE_MAP and key != 'cut':
        return RULE_MAP[key]
    for rule in RULES:
        if any(word in name for word in rule['aliases']):
            return rule
    return None

def estimate(name, captured_on, key=None, condition='whole', zone='蔬果'):
    if zone == '冷冻':
        return None
    rule = find_rule(name, key, condition)
    if not rule:
        return None
    start = date.fromisoformat(captured_on)
    days = rule['days']
    if condition == 'cut':
        whole = find_rule(name, key, 'whole')
        if whole:
            days = min(days, whole['days'])
    return dict(rule_key=rule['key'], days=days, planned_until=(start + timedelta(days=days)).isoformat(),
                source=rule['source'], reference_range=rule['range'], note=rule['note'], basis='拍摄日期 + 冷藏建议天数')

def public_rules():
    return [dict(r, aliases=list(r['aliases'])) for r in RULES]
