import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('memory', ROOT / 'skills/road-disease-memory/scripts/memory.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def record(kind='inspection', project='demo'):
    r = dict(kind=kind, project=project, title='坑槽巡检', summary='模拟样本，尚无尺寸标定', observed_at='2026-10-07T09:00:00+08:00', review='verified', sources=[dict(uri='demo://synthetic', note='合成测试资料')], diseases=['坑槽'], road='示例路段')
    if kind == 'experiment':
        r['payload'] = dict(model='yolo12s', comparison=dict(dataset_sha256='a'*64, classes_sha256='b'*64, split='test', evaluation_protocol='demo-v1', image_size=640), metrics=dict(map50=0.7))
    return r


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.mem = m.Memory(self.root / 'store')
        self.mem.init()

    def tearDown(self):
        self.tmp.cleanup()

    def test_persists_after_reopening(self):
        r = self.mem.add(record())
        self.assertEqual(m.Memory(self.root/'store').get(r['id'])['title'], '坑槽巡检')

    def test_project_isolation_and_chinese_search(self):
        self.mem.add(record()); self.mem.add(record(project='other'))
        self.assertEqual(len(self.mem.recall('demo', '坑槽', road='示例路段', disease='坑槽')), 1)
        self.assertEqual(self.mem.recall('missing'), [])

    def test_revision_retains_history_and_rejects_stale_update(self):
        first = self.mem.add(record())
        revised = record(); revised['summary'] = '现场复核后更新'
        second = self.mem.add(revised, first['id'])
        self.assertEqual(self.mem.get(first['id'])['superseded_by'], second['id'])
        self.assertEqual(len(self.mem.recall('demo')), 1)
        self.assertEqual(len(self.mem.recall('demo', history=True)), 2)
        with self.assertRaises(ValueError): self.mem.add(revised, first['id'])

    def test_rejected_excluded_from_default_recall(self):
        r = record(); r['review'] = 'rejected'; self.mem.add(r)
        self.assertEqual(self.mem.recall('demo'), [])
        self.assertEqual(len(self.mem.recall('demo', history=True)), 1)

    def test_source_and_timezone_required(self):
        for key, value in [('sources', []), ('observed_at', '2026-10-07'), ('review', 'guessed')]:
            r = record(); r[key] = value
            with self.assertRaises(ValueError): self.mem.add(r)

    def test_metric_validation(self):
        for value in [float('nan'), float('inf'), 70, True]:
            r = record('experiment'); r['payload']['metrics']['map50'] = value
            with self.assertRaises(ValueError): self.mem.add(r)

    def test_comparison_requires_dataset_identity(self):
        r = record('experiment'); del r['payload']['comparison']['dataset_sha256']
        with self.assertRaises(ValueError): self.mem.add(r)

    def test_best_never_mixes_datasets_or_unverified_runs(self):
        first = self.mem.add(record('experiment'))
        other = record('experiment'); other['payload']['comparison']['dataset_sha256'] = 'c'*64; other['payload']['metrics']['map50'] = 0.99
        self.mem.add(other)
        provisional = record('experiment'); provisional['review'] = 'provisional'; provisional['payload']['metrics']['map50'] = 0.98
        self.mem.add(provisional)
        result = self.mem.best('demo', first['id'], 'map50', 'max')
        self.assertEqual(result['compared'], 1)
        self.assertEqual(result['winners'][0]['id'], first['id'])
        self.assertFalse(result['winners'][0]['weights_available'])

    def test_best_ties_and_minimum(self):
        first = self.mem.add(record('experiment')); self.mem.add(record('experiment'))
        self.assertEqual(len(self.mem.best('demo', first['id'], 'map50', 'min')['winners']), 2)

    def test_archive_survives_source_removal_and_detects_tampering(self):
        r = self.mem.add(record('experiment'))
        source = self.root/'synthetic.bin'; source.write_bytes(b'not real model weights')
        artifact = self.mem.attach(r['id'], source, 'weights', 'Synthetic artifact only')
        source.unlink()
        self.assertTrue(self.mem.audit()['ok'])
        self.assertTrue(self.mem.best('demo', r['id'], 'map50', 'max')['winners'][0]['weights_available'])
        Path(artifact['path']).write_bytes(b'corrupt')
        self.assertFalse(self.mem.audit()['ok'])
        self.assertFalse(self.mem.best('demo', r['id'], 'map50', 'max')['winners'][0]['weights_available'])

    def test_contradictions_are_visible_and_cross_project_links_rejected(self):
        a = self.mem.add(record()); b = self.mem.add(record()); c = self.mem.add(record(project='other'))
        self.mem.link(a['id'], 'contradicts', b['id'], '需现场复核')
        self.assertEqual(self.mem.get(a['id'])['relations'][0]['relation'], 'contradicts')
        with self.assertRaises(ValueError): self.mem.link(a['id'], 'supports', c['id'], 'x')

    def test_task_calls_preserve_specific_revision_ids(self):
        a = self.mem.add(record())
        packet = self.mem.brief('demo', '下一轮巡检')
        self.mem.add(record(), a['id'])
        with self.mem.connect() as con:
            row = con.execute('SELECT record_ids FROM calls WHERE id=?', (packet['call_id'],)).fetchone()
        self.assertIn(a['id'], row['record_ids'])

    def test_backup_reopens_and_restores_artifacts(self):
        a = self.mem.add(record()); file = self.root/'data.bin'; file.write_bytes(b'evidence')
        self.mem.attach(a['id'], file, 'evidence', 'test')
        self.mem.backup(self.root/'backup')
        restored = m.Memory(self.root/'backup')
        self.assertTrue(restored.audit()['ok'])
        self.assertEqual(restored.get(a['id'])['title'], a['title'])
        with self.assertRaises(FileExistsError): self.mem.backup(self.root/'backup')

    def test_dashboard_escapes_content_and_records_calls(self):
        r = record(); r['title'] = '<script>alert(1)</script>'; self.mem.add(r)
        self.mem.brief('demo', '模拟任务')
        path = self.root/'report.html'; self.mem.dashboard('demo', path)
        page = path.read_text(encoding='utf-8')
        self.assertNotIn('<script>', page)
        self.assertIn('&lt;script&gt;', page)
        self.assertIn('模拟任务', page)


if __name__ == '__main__': unittest.main()
