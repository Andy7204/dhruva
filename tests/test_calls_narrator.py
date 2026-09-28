import copy
import hashlib
import unittest
from unittest.mock import patch
from scripts.show_call import render_call
from qlab import narrator


class CallTests(unittest.TestCase):
    def setUp(self):
        self.state={'as_of':'2026-09-28','history':[['2026-09-28',1000]],
                    'step_count':8,'risk_on':False,'breaker':True,'next_rebalance_in':55,
                    'holdings':{'TEST.NS':{}},'orders':[{'status':'scheduled','side':'SELL',
                    'symbol':'TEST.NS','reason':'breaker'}]}
        self.results=[{'name':'balanced','capital':1000,'value':1000,'as_of':'2026-09-28','state':self.state}]

    def test_cli_uses_saved_intents_and_withholds_stale_calls(self):
        health={'status':'OPERATIONAL','problems':[],'warnings':[],'books':self.results}
        self.assertIn('pending paper intent',render_call(health))
        self.assertNotIn('win-case',render_call(health))
        health['problems']=['PORTFOLIO STALE']
        text=render_call(health)
        self.assertIn('WITHHELD',text)
        self.assertNotIn('SELL TEST',text)

    def test_narration_preserves_orders_and_labels_pending_sales(self):
        before=copy.deepcopy(self.results)
        with patch('qlab.narrator._llm',return_value=None):
            output=narrator.narrate_with_metadata({'base_currency':'INR'},self.results)
        self.assertEqual(self.results,before)
        self.assertEqual(output['source'],'rules')
        self.assertIn('not a completed sale',output['text'])
        self.assertIn('TEST.NS',output['text'])
        self.assertNotIn('it has de-risked',output['text'])
        self.assertEqual(output['text_sha256'],hashlib.sha256(output['text'].encode()).hexdigest())

    def test_ai_words_are_unverified_and_cannot_change_book(self):
        before=copy.deepcopy(self.results)
        with patch.dict('os.environ',{'ANTHROPIC_API_KEY':'fixture'}),patch('qlab.narrator._llm',return_value='invented wording'):
            output=narrator.narrate_with_metadata({'base_currency':'INR'},self.results)
        self.assertEqual(output['source'],'anthropic')
        self.assertIn('unverified',output['text'])
        self.assertEqual(self.results,before)
