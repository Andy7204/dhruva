import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from qlab import livebook, report


class ReportAccountingTests(unittest.TestCase):
    def test_report_uses_saved_nav_and_shared_tax_once(self):
        cfg={'base_currency':'INR','starting_capital':50000,'books':{}}
        results=[]
        for name in ('balanced','aggressive'):
            st=livebook.new_livebook(cfg,name)
            st.update(as_of='2026-09-24',inception='2026-09-24',step_count=1,
                history=[['2026-09-24',49950]],tax_accrued=50,
                tax_scope='SHARED_PAPER_ACCOUNT',tax_detail={'2026':{'tax':100}})
            results.append({'name':name,'state':st,'capital':50000,'prices_now':{}})
        with tempfile.TemporaryDirectory() as tmp,patch.object(report,'_load_backtest',return_value={}),patch.object(report,'_load_validation',return_value={}):
            path=report.build_multi_dashboard(cfg,results,pd.Series([100.],index=pd.to_datetime(['2026-09-24'])),out_path=Path(tmp)/'report.html')
            html=path.read_text(encoding='utf-8')
            self.assertIn('99,900',html)
            self.assertEqual(html.count('FY 2026 shared account'),1)
