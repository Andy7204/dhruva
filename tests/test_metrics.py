import json
import unittest
import numpy as np
import pandas as pd
from qlab.metrics import compute_metrics


class MetricsTests(unittest.TestCase):
    def test_one_year_has_252_returns_not_253(self):
        result=compute_metrics(pd.Series(np.geomspace(100,110,253)),[])
        self.assertEqual(result['return_periods'],252)
        self.assertEqual(result['cagr_pct'],10.)

    def test_two_observations_keep_actual_loss(self):
        result=compute_metrics(pd.Series([100,80]),[])
        self.assertEqual(result['total_return_pct'],-20)
        self.assertEqual(result['max_drawdown_pct'],-20)
        self.assertFalse(result['annualization_available'])

    def test_invalid_curves_fail_instead_of_hiding_rows(self):
        for values in ([100,float('nan'),110],[100,float('inf')],[100,0]):
            with self.assertRaises(ValueError): compute_metrics(pd.Series(values),[])
        with self.assertRaises(ValueError): compute_metrics(pd.Series([100,110],index=[1,1]),[])
        with self.assertRaises(ValueError): compute_metrics(pd.Series([100,110],index=[2,1]),[])

    def test_no_losses_is_not_fake_999_profit_factor(self):
        result=compute_metrics(pd.Series([100,110,120]),[{'net_pnl':20}])
        self.assertIsNone(result['profit_factor'])
        self.assertEqual(result['profit_factor_status'],'NO_LOSSES')
        json.dumps(result,allow_nan=False)
        mixed=compute_metrics(pd.Series([100,110,120]),[{'net_pnl':20},{'net_pnl':-10}])
        self.assertEqual(mixed['profit_factor'],2.)
