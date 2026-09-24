import copy
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd

from dhruva.data_quality import validate_inputs, DataQualityError
from qlab.data import clean_ohlc
from qlab.indicators import enrich, atr


def bars():
    dates = pd.bdate_range(end='2026-09-23', periods=260)
    close = np.linspace(90,100,len(dates))
    return pd.DataFrame(dict(open=close,high=close+2,low=close-2,close=close,
                             adjclose=close,volume=1000.), index=dates)


class DataQualityTests(unittest.TestCase):
    def test_clean_and_indicators_prefix_independent(self):
        df=bars(); df.loc[df.index[40],'adjclose']=200
        short=clean_ohlc(df.iloc[:100]); long=clean_ohlc(df)
        pd.testing.assert_frame_equal(short,long.loc[:df.index[99]])
        pd.testing.assert_frame_equal(enrich(short),enrich(long).loc[:df.index[99]])

    def test_atr_uses_same_adjusted_units(self):
        df=bars(); df['adjclose']*=.5
        result=enrich(df)
        expected=atr(df.assign(high=df.high*.5,low=df.low*.5,close=df.close*.5),14)
        pd.testing.assert_series_equal(result.atr14,expected,check_names=False)

    def gate(self, data, bench=None, held=False, coverage=1.):
        with tempfile.TemporaryDirectory() as tmp:
            return validate_inputs({'TEST':data}, bars() if bench is None else bench,
                {'universe':['TEST'],'regime':{'benchmark':'INDEX'},'data':{'minimum_coverage':coverage}},
                {'book':{'holdings':{'TEST':{'qty':1}} if held else {}}}, Path(tmp),expected='2026-09-23')

    def test_latest_corrupt_stale_duplicates_missing_zero_and_outage_block(self):
        variations=[]
        df=bars(); df.iloc[-1,df.columns.get_loc('high')]=1; variations.append(df)
        variations.append(bars().iloc[:-1])
        variations.append(pd.concat([bars(),bars().iloc[-1:]]))
        variations.append(bars().drop(columns='volume'))
        df=bars(); df.iloc[-1,df.columns.get_loc('volume')]=0; variations.append(df)
        df=bars(); df.attrs['fetch_error']='mock network down'; variations.append(df)
        for data in variations:
            with self.subTest(kind=str(data.tail(1))):
                with self.assertRaises(DataQualityError): self.gate(data)

    def test_held_exclusion_fatal_even_when_coverage_tolerates_it(self):
        with self.assertRaisesRegex(DataQualityError,'HELD TEST'):
            self.gate(bars().iloc[:-1],held=True,coverage=0.)

    def test_benchmark_missing_is_fatal(self):
        with self.assertRaisesRegex(DataQualityError,'BENCHMARK'):
            self.gate(bars(),bench=bars().iloc[:-1])

    def test_future_bar_excluded_and_index_zero_volume_allowed(self):
        df=bars(); df.loc[pd.Timestamp('2026-09-24')]=df.iloc[-1]
        benchmark=bars(); benchmark['volume']=0
        valid,_,report=self.gate(df,benchmark)
        self.assertEqual(valid['TEST'].index[-1],pd.Timestamp('2026-09-23'))
        self.assertEqual(report['symbols']['TEST']['future_or_unfinished_rows_excluded'],1)


if __name__ == '__main__': unittest.main()
