"""Create only synthetic demonstration data in a NEW directory."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('memory', ROOT / 'skills/road-disease-memory/scripts/memory.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='local-data/demo')
    args = parser.parse_args()
    target = Path(args.output).resolve()
    if target.exists():
        raise SystemExit('Choose a new output directory; existing demo will not be overwritten.')
    mem = m.Memory(target / 'store'); mem.init()
    project = '模拟演示：道路病害研究（非真实实验）'
    ids = {}
    for kind, title, summary in [
        ('inspection', '模拟巡检：A 路段坑槽', '演示记录。发现疑似坑槽，暂无尺寸和深度标定。'),
        ('sample', '模拟病害样本索引', '样本仅用作记录结构演示，不包含真实图片。'),
        ('diagnosis', '模拟诊断依据摘要', '暂列水损害为候选原因，需要现场排水与结构检测验证。'),
        ('standard', '规范引用记忆示例', '示例展示如何保存规范来源；当前有效性仍需查证。'),
        ('recommendation', '待验证建议', '建议补充真实尺寸与排水调查；这是模拟建议，不用于工程实施。'),
        ('feedback', '模拟后续反馈', '演示后续巡检记录与原建议建立关联，不代表真实养护效果。')]:
        row = dict(kind=kind, project=project, title=title, summary=summary, observed_at='2026-10-07T10:00:00+08:00', review='provisional', road='模拟 A 路段', diseases=['坑槽'], sources=[dict(uri='demo://synthetic/'+kind, note='完全模拟的功能演示数据')])
        ids[kind] = mem.add(row)['id']
    scope = dict(dataset_sha256=hashlib.sha256(b'synthetic-dataset-manifest').hexdigest(), classes_sha256=hashlib.sha256(b'synthetic-classes').hexdigest(), split='synthetic-test', evaluation_protocol='synthetic-protocol-v1', image_size=640)
    for model, metric in [('YOLO12s-demo', .61), ('YOLO12m-demo', .65)]:
        row = dict(kind='experiment', project=project, title=model+'：模拟实验', summary='人为设定的演示数值，不是模型实测性能。', observed_at='2026-10-07T10:00:00+08:00', review='verified', sources=[dict(uri='demo://synthetic/metrics', note='仅验证演示输入与归档一致，不验证模型性能')], payload=dict(model=model, comparison=scope, metrics=dict(map50_95=metric, map50=metric+.1)))
        ids[model] = mem.add(row)['id']
    artifact = target/'DEMO_NOT_A_MODEL.txt'
    artifact.write_text('Synthetic placeholder. This is NOT a loadable model checkpoint.\n', encoding='utf-8')
    mem.attach(ids['YOLO12m-demo'], artifact, 'weights', '模拟权重占位文本，仅演示复制归档和哈希，不可加载为模型')
    mem.link(ids['feedback'], 'follows_up', ids['recommendation'], '模拟后续任务回访')
    mem.link(ids['diagnosis'], 'supports', ids['recommendation'], '仅演示证据关系，不代表原因已证实')
    mem.brief(project, '未来任务：检索 A 路段坑槽历史', query='坑槽')
    mem.brief(project, '未来任务：复用模型比较依据', query='模拟实验')
    comparison = mem.best(project, ids['YOLO12s-demo'], 'map50_95', 'max')
    (target/'comparison.json').write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding='utf-8')
    mem.backup(target/'backup')
    result = mem.dashboard(project, target/'dashboard.html')
    (target/'record-ids.json').write_text(json.dumps(ids, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({**result, 'audit': mem.audit(), 'synthetic_only': True}, ensure_ascii=False))


if __name__ == '__main__': main()
