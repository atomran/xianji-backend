"""日期计算、到期状态机 — 从 backend/domain.py 零改动迁移。"""
from datetime import date, timedelta
import calendar

ZONES = ('冷藏', '冷冻', '蔬果')

def valid_date(value):
    if not value:
        return None
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('日期格式应为 YYYY-MM-DD')
    return parsed

def validate(item):
    if not isinstance(item.get('name'), str) or not 1 <= len(item['name'].strip()) <= 80:
        raise ValueError('请填写食物名称（最多 80 字）')
    item['name'] = item['name'].strip()
    if item.get('zone') not in ZONES:
        raise ValueError('请选择冷藏、冷冻或蔬果')
    if type(item.get('quantity')) is not int or not 1 <= item['quantity'] <= 999:
        raise ValueError('数量应为 1–999 的整数')
    for key in ('produced_on', 'expires_on', 'opened_on', 'planned_until', 'captured_on'):
        valid_date(item.get(key))
    for key in ('shelf_days', 'opened_days'):
        value = item.get(key)
        if value is not None and (type(value) is not int or not 1 <= value <= 3650):
            raise ValueError('期限应为 1–3650 天的整数')
    if item.get('kind') not in (None, 'packaged', 'produce', 'other'):
        raise ValueError('食物类型无效')
    amount = item.get('shelf_value')
    if amount is not None:
        unit = item.get('shelf_unit')
        if unit not in ('days', 'months', 'years') or type(amount) is not int or not 1 <= amount <= {'days': 3650, 'months': 120, 'years': 10}[unit]:
            raise ValueError('请检查保质期数值和单位')
    if item.get('estimate_days') is not None:
        if type(item['estimate_days']) is not int or not 1 <= item['estimate_days'] <= 90 or not item.get('captured_on'):
            raise ValueError('估算需要拍摄日期和 1–90 天的保存天数')
        if item.get('kind') != 'produce':
            raise ValueError('建议保存天数仅适用于蔬果')
    if item.get('condition') not in (None, 'whole', 'cut', 'unknown'):
        raise ValueError('蔬果状态无效')
    if item.get('opened_days') and not item.get('opened_on'):
        raise ValueError('请补充开封日期')
    if item.get('expires_on') and item.get('produced_on') and item['expires_on'] < item['produced_on']:
        raise ValueError('到期日期不能早于生产日期')
    if len(item.get('note', '')) > 1000:
        raise ValueError('备注最多 1000 字')
    if item.get('status', 'active') not in ('active', 'consumed', 'discarded'):
        raise ValueError('库存状态无效')
    return item

def deadline(item):
    limits = []
    if item.get('expires_on'):
        limits.append((item['expires_on'], '包装到期'))
    elif item.get('produced_on') and item.get('shelf_value') and item.get('shelf_unit') in ('days', 'months', 'years'):
        d = valid_date(item['produced_on']); value = item['shelf_value']; unit = item['shelf_unit']
        if unit == 'days':
            due = d + timedelta(days=value)
        else:
            index = d.year * 12 + d.month - 1 + value * (12 if unit == 'years' else 1)
            year, month = divmod(index, 12); month += 1
            due = date(year, month, min(d.day, calendar.monthrange(year, month)[1]))
        limits.append((due.isoformat(), '计算到期'))
    elif item.get('produced_on') and item.get('shelf_days'):
        limits.append(((valid_date(item['produced_on']) + timedelta(days=item['shelf_days'])).isoformat(), '计算到期'))
    if item.get('opened_on') and item.get('opened_days'):
        limits.append(((valid_date(item['opened_on']) + timedelta(days=item['opened_days'])).isoformat(), '开封期限'))
    if item.get('kind') == 'produce' and item.get('captured_on') and item.get('estimate_days'):
        limits.append(((valid_date(item['captured_on']) + timedelta(days=item['estimate_days'])).isoformat(), '蔬果预估'))
    elif item.get('planned_until'):
        limits.append((item['planned_until'], '计划食用'))
    return min(limits) if limits else (None, '待补日期')

def decorate(item, today):
    due, basis = deadline(item)
    days = (valid_date(due) - today).days if due else None
    state = 'unknown' if days is None else 'overdue' if days < 0 else 'today' if days == 0 else 'soon' if days <= 3 else 'fresh'
    return dict(item, due_on=due, due_basis=basis, days_left=days, urgency=state, is_estimated=basis in ('蔬果预估', '计划食用'))

def ordered(items, today):
    result = [decorate(i, today) for i in items if i.get('status', 'active') == 'active']
    return sorted(result, key=lambda i: (i['due_on'] or '9999-12-31', i['name'], i.get('id', '')))
