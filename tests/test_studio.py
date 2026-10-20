import unittest, sys, json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'src'))
from engine import run

class StudioTests(unittest.TestCase):
 def sample(self):return json.loads((R/'examples/studio.json').read_text())
 def execute(self,**changes):
  p=self.sample();p.update(changes);return run(p)['lab']
 def test_json_serializable(self):json.dumps(run(self.sample()),allow_nan=False)
 def test_row_and_contract_count(self):
  l=self.execute();self.assertEqual(l['record_count'],80);self.assertEqual(len(l['checks']),4)
 def test_unique_marks_all_duplicate_members(self):
  l=self.execute(csv='id,x\n1,a\n1,b',baseline='',rules='[{"column":"id","type":"unique"}]');self.assertEqual(l['checks'][0]['rows'],[2,3])
 def test_missing_map_has_exact_coordinate(self):
  l=self.execute(csv='id,x\n1,',baseline='',rules='[{"column":"x","type":"not_null"}]');self.assertEqual(l['matrix'][0]['cells'][1]['state'],'violation')
 def test_equal_baseline_has_zero_psi(self):
  p=self.sample();l=self.execute(csv=p['baseline']);self.assertTrue(all(x['psi']==0 for x in l['drift']))
 def test_range_boundaries_inclusive(self):
  l=self.execute(csv='n\n0\n10\n11',baseline='',rules='[{"column":"n","type":"range","min":0,"max":10}]');self.assertEqual(l['checks'][0]['rows'],[4])
 def test_schema_add_remove_detected(self):
  l=self.execute(csv='a,c\n1,2',baseline='a,b\n1,2',rules='[]');self.assertEqual({x['status'] for x in l['drift']},{'stable','new column','removed column'})
 def test_invalid_contract_rejected(self):
  with self.assertRaises(ValueError):self.execute(rules='[{"column":"missing","type":"unique"}]')
 def test_reverse_range_rejected(self):
  with self.assertRaises(ValueError):self.execute(rules='[{"column":"amount","type":"range","min":10,"max":2}]')
 def test_no_contract_has_no_score(self):self.assertIsNone(self.execute(rules='[]')['score'])
 def test_distribution_bins_normalized(self):
  for d in self.execute()['drift']:
   self.assertAlmostEqual(sum(b['current'] for b in d['bins']),100,delta=.1)
