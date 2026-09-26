import copy
import json
from pathlib import Path
import unittest
import tempfile
import hashlib
from qlab import income, livebook, tax, accounting, lots


class IncomeTests(unittest.TestCase):
    def setUp(self):
        self.cfg=json.loads(Path('config.json').read_text(encoding='utf-8'))
        self.state=livebook.new_livebook(self.cfg,'balanced')
        self.state.update(cash=0.,price_convention='actual_quoted_units')
        self.inventory={}
        self.receipt={'id':'fixture1','book':'balanced','symbol':'LIQUIDBEES.NS',
            'gross':100.,'withheld':10.,'taxable_date':'2026-09-25','effective_date':'2026-09-25',
            'retrieved_at':'2026-09-25T12:00:00+00:00','source_url':'https://example.org/fixture',
            'source_sha256':'a'*64,'mode':'cash'}

    def post(self):
        return income.post_receipt(self.state,self.inventory,self.receipt,'2026-09-25')

    def verify(self,prices):
        tax.reserve_accounts({'balanced':self.state},self.cfg)
        self.state['account_tax_inventory']=copy.deepcopy(self.inventory)
        self.state['history']=[['2026-09-25',livebook.total_value(self.state,prices)]]
        return accounting.verify([{'state':self.state,'prices_now':prices}],self.cfg)

    def test_cash_tds_is_asset_and_gross_income_taxed_once(self):
        self.assertTrue(self.post())
        self.assertEqual(self.state['cash'],90.)
        self.assertEqual(self.state['tax_prepaid'],10.)
        self.assertEqual(self.verify({})['nav'],68.8)
        before=copy.deepcopy(self.state)
        self.assertFalse(self.post())
        self.assertEqual(self.state,before)
        self.receipt['gross']=101.
        with self.assertRaisesRegex(ValueError,'identity changed'): self.post()

    def test_fractional_allotment_basis_and_tax_reconcile(self):
        self.receipt.update(mode='reinvested_units',gross=3.,withheld=0.,units=.003,unit_price=1000.)
        self.post()
        holding=self.state['holdings']['LIQUIDBEES.NS']
        self.assertEqual(holding['qty'],.003)
        self.assertEqual(holding['lots'][0]['tax_cost'],3.)
        self.assertEqual(self.verify({'LIQUIDBEES.NS':1000})['nav'],2.06)

    def test_bad_allotment_is_atomic_and_adjusted_units_rejected(self):
        self.receipt.update(mode='reinvested_units',units=.003,unit_price=1000.)
        before=copy.deepcopy(self.state)
        with self.assertRaisesRegex(ValueError,'reconciliation failed'): self.post()
        self.assertEqual(self.state,before);self.assertEqual(self.inventory,{})
        self.state['price_convention']='adjusted'
        with self.assertRaisesRegex(ValueError,'actual quoted units'): self.post()

    def test_late_future_and_unobserved_receipts(self):
        self.receipt['effective_date']='2026-09-24'
        with self.assertRaisesRegex(ValueError,'explicit ledger correction'): self.post()
        self.receipt['effective_date']='2026-09-26'
        self.assertFalse(self.post())
        self.receipt['retrieved_at']='2026-09-26T12:00:00+00:00'
        self.receipt['effective_date']='2026-09-25'
        with self.assertRaisesRegex(ValueError,'after the evaluation'): self.post()

    def test_weekend_receipt_can_be_recorded_next_unprocessed_session(self):
        self.receipt.update(effective_date='2026-09-20',taxable_date='2026-09-20',
                            retrieved_at='2026-09-21T12:00:00+00:00')
        self.assertTrue(income.post_receipt(self.state,self.inventory,self.receipt,'2026-09-21','2026-09-18'))

    def test_fifo_sale_keeps_fractional_remainder_in_later_buy_lot(self):
        holding={};fees={'total':0.,'stt':0.}
        lots.buy(holding,.003,3.,fees,'2026-09-20','distribution')
        lots.buy(holding,1,1000.,fees,'2026-09-21','buy')
        lots.sell(holding,1,1000.,fees,'2026-09-25','LIQUIDBEES.NS','sell')
        self.assertEqual(holding['qty'],.003)
        self.assertEqual(holding['lots'][0]['id'],'buy')
        accounting._verify_inventory({'LIQUIDBEES.NS':holding})

    def test_source_bytes_are_required_and_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.json';path.write_bytes(b'fixture')
            receipt={'source_path':'source.json','source_sha256':hashlib.sha256(b'fixture').hexdigest()}
            income.verify_source(tmp,receipt)
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'hash mismatch'): income.verify_source(tmp,receipt)
