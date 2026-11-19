"""Run the production DOM reader against mixed and corrupted offer documents."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

CORE = Path(__file__).resolve().parents[1] / 'core'

@unittest.skipUnless(shutil.which('node'), 'Node is needed to exercise the DOM reader')
class CombinedOfferDomTests(unittest.TestCase):
    def read(self, ids=(1, 3), **changes):
        source = (CORE/'cardmarket-combined-offers.ps1').read_text(encoding='utf-8-sig')
        expression = source.split("$expression=@'\n", 1)[1].split("\n'@", 1)[0]
        expression = expression.replace('__IDS__', json.dumps(list(ids))).replace('__REVERSE__', 'Y').replace('__FIRST__', '0')
        fixture = {
            'query': 'language='+','.join(map(str, ids))+'&minCondition=2&isSigned=N&isAltered=N&isReverseHolo=Y',
            'checked': list(ids), 'reverse': 'Y', 'signed': 'N', 'altered': 'N',
            'conditions': ['Near Mint', 'Mint'], 'languages': ['Deutsch', 'English'],
        }
        fixture.update(changes)
        script = r'''
const vm=require('node:vm');
const [fixture, expression]=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
const f={action:'Product_Filter_FilterProduct',elements:{namedItem(name){
 const fields={minCondition:'2','extra[isSigned]':fixture.signed,'extra[isAltered]':fixture.altered,'extra[isReverseHolo]':fixture.reverse};
 return name in fields?{value:fields[name]}:null;
}}};
const rows=fixture.languages.map((language,i)=>({id:'article-'+i,
 querySelector(s){if(s==='.article-condition')return {getAttribute(){return fixture.conditions[i]}};
 if(s==='.price-container')return {textContent:i?'9,00 EUR':'1,00 EUR'};return null;},
 querySelectorAll(){return [language,'Reverse Holo'].map(title=>({getAttribute(){return title}}));}
}));
const document={forms:[f],querySelector(s){if(s==='input[name=idProduct]')return {value:'751539'};return null;},
 querySelectorAll(s){if(s==='input')return fixture.checked.map(id=>({name:'language['+id+']',checked:true}));
 if(s==='.article-row')return rows;return [];}};
process.stdout.write(vm.runInNewContext(expression,{document,URL,location:{href:'https://www.cardmarket.com/de/Pokemon/Products/Singles/Paldean-Fates/Heat-Rotom-PAF013?'+fixture.query}}));
'''
        result = subprocess.run(['node', '-e', script], input=json.dumps([fixture, expression]), text=True, capture_output=True, check=True)
        return json.loads(result.stdout)

    def test_combined_document_preserves_each_language(self):
        result = self.read()
        self.assertTrue(result['filtered'])
        self.assertEqual(result['productId'], '751539')
        self.assertEqual([r['language'] for r in result['rows']], ['Deutsch', 'English'])
        self.assertEqual([r['price'] for r in result['rows']], ['1,00 EUR', '9,00 EUR'])
        self.assertFalse(result['hasMore'])

    def test_single_language_uses_the_same_filter_checks(self):
        self.assertTrue(self.read(ids=(3,), languages=['Deutsch'])['filtered'])
        self.assertTrue(self.read(ids=(1,), languages=['English'])['filtered'])

    def test_url_and_dom_must_both_confirm_the_exact_languages_and_flags(self):
        for changes in (
            {'checked': [3]}, {'checked': [1, 3, 4]}, {'checked': [1, 1, 3]},
            {'query': 'language=3&minCondition=2&isSigned=N&isAltered=N&isReverseHolo=Y'},
            {'query': 'language=1,3&minCondition=3&isSigned=N&isAltered=N&isReverseHolo=Y'},
            {'reverse': 'N'}, {'signed': 'Y'}, {'altered': 'Y'},
        ):
            with self.subTest(changes=changes):
                self.assertFalse(self.read(**changes)['filtered'])

if __name__ == '__main__':
    unittest.main()
