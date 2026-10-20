import unittest,sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'src'))
from engine import run
from common import read_csv
class EngineTests(unittest.TestCase):
 def sample(self):return json.loads((R/'examples/sample.json').read_text())
 def test_empty_csv_rejected(self):
  with self.assertRaises(ValueError):read_csv('')
 def test_duplicate_headers_rejected(self):
  with self.assertRaises(ValueError):read_csv('a,a\n1,2')
 def test_ragged_csv_rejected(self):
  with self.assertRaises(ValueError):read_csv('a,b\n1')
 def test_quoted_csv_and_bom(self):
  h,r=read_csv('\ufeffid,note\n1,"hello, world"');self.assertEqual(r[0]['note'],'hello, world')
 def test_sample_completeness_and_duplicate(self):
  r=run(self.sample());self.assertEqual(r['metrics'][0]['value'],7);self.assertEqual(r['metrics'][3]['value'],1);self.assertTrue(any('required' in f['title']for f in r['findings']))
 def test_null_token_case_insensitive(self):
  r=run({'csv':'id,email\n1,NULL\n2,N/A','required':'email'});self.assertEqual(r['table']['rows'][1][3],'2')
 def test_unique_strings_not_coerced(self):
  r=run({'csv':'id\n001\n1','unique':'id'});self.assertFalse(any(f['severity']=='error'for f in r['findings']))
 def test_unknown_rule_column(self):
  with self.assertRaises(ValueError):run({'csv':'id\n1','required':'unknown'})
 def test_nonfinite_not_numeric(self):
  r=run({'csv':'value\nNaN\nInfinity'});self.assertEqual(r['table']['rows'][0][1],'text')
 def test_outlier_signal(self):
  r=run({'csv':'x\n1\n2\n3\n4\n1000'});self.assertTrue(any('outlier'in f['title']for f in r['findings']))

if __name__=='__main__':unittest.main()
