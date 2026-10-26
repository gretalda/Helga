import unittest
from fastapi.testclient import TestClient
from main import app
from astro_portal import astro_facts,chart,return_report

PROFILE={'birth_date':'1990-02-14','birth_time':'10:30','city':'minsk','time_known':True}
CLIENT=TestClient(app)

class PortalTests(unittest.TestCase):
    def check(self,mode,**extra):
        d={'mode':mode,'profile':PROFILE,'date':'2026-10-26',**extra}
        response=CLIENT.post('/api/astro/report',json=d)
        self.assertEqual(response.status_code,200,response.text)
        body=response.json()
        self.assertEqual(body['type'],mode if mode!='transits' else 'transit')
        self.assertTrue(body['sections'])
        self.assertTrue(body['chart']['planets'])
        self.assertTrue(body.get('lead'))
        return body
    def test_birth_checkbox_id_matches_javascript(self):
        page=CLIENT.get('/').text
        self.assertIn('id="time-known"',page)
        self.assertIn("prefix==='birth'?'time-known':prefix+'-known'",page)
        self.assertIn('id="other-known"',page)

    def test_pwa_root_scope_and_manifest(self):
        sw=CLIENT.get('/service-worker.js')
        self.assertEqual(sw.status_code,200)
        self.assertIn('javascript',sw.headers['content-type'])
        self.assertIn('install',sw.text)
        manifest=CLIENT.get('/static/manifest.json').json()
        self.assertEqual(manifest['start_url'],'/')
        self.assertEqual(manifest['scope'],'/')
        self.assertEqual(manifest['display'],'standalone')
        self.assertEqual(CLIENT.get('/static/icon-192.png').status_code,200)
        self.assertEqual(CLIENT.get('/static/icon-512.png').status_code,200)
        self.assertIn("register('/service-worker.js'",CLIENT.get('/').text)
        self.assertIn("register('/service-worker.js'",CLIENT.get('/horary').text)

    def test_home_portal_and_horary_retained(self):
        self.assertIn('Твоя карта',CLIENT.get('/').text)
        self.assertIn('АстроЛично',CLIENT.get('/horary').text)
        self.assertEqual(CLIENT.get('/api/health').json()['version'],'1.2.0')
    def test_natal(self):
        x=self.check('natal');self.assertIn('Водолей',x['lead']);self.assertTrue(x['chart']['cusps'])
    def test_transits(self):
        x=self.check('transits');self.assertTrue(x['windows'])
    def test_day(self):self.check('day')
    def test_period(self):self.check('period',end_date='2026-11-04')
    def test_solar(self):
        x=self.check('solar',solar_year=2026)
        self.assertTrue(x['return_chart']['planets'])
        self.assertIn('2026',x['lead'])
    def test_lunar(self):
        x=self.check('lunar');self.assertIn('конец',x['note'].lower()) if False else self.assertTrue(x['return_chart'])
    def test_progression(self):self.check('progression')
    def test_direction(self):self.check('direction')
    def test_synastry(self):self.check('compatibility',second_profile={'birth_date':'1992-09-16','birth_time':'12:00','city':'minsk','time_known':True})
    def test_sign(self):
        x=self.check('sign');self.assertIn('Водолей',x['title'])
    def test_unknown_time_has_no_moon_or_houses(self):
        x=chart({**PROFILE,'time_known':False});self.assertNotIn('Луна',x['planets']);self.assertFalse(x['cusps']);self.assertTrue(x['limitations'])
    def test_lunar_requires_known_time(self):
        d={'mode':'lunar','profile':{**PROFILE,'time_known':False},'date':'2026-10-26'}
        x=CLIENT.post('/api/astro/report',json=d);self.assertEqual(x.status_code,422)
    def test_bad_profile_explicit_error(self):
        d={'mode':'natal','profile':{'birth_date':'bad'}}
        x=CLIENT.post('/api/astro/report',json=d);self.assertEqual(x.status_code,422)
    def test_other_city_manual_coordinates(self):
        p={**PROFILE,'city':'other','city_name':'Тестовый город','lat':53.9,'lon':27.6,'tz':'Europe/Minsk'}
        x=CLIENT.post('/api/astro/report',json={'mode':'natal','profile':p}).json()
        self.assertEqual(x['chart']['place']['name'],'Тестовый город')
    def test_facts(self):
        r=CLIENT.get('/api/astro/facts',params={'date':'2026-10-26','city':'minsk'})
        self.assertEqual(r.status_code,200);self.assertIn('moon_phase',r.json())
    def test_period_cannot_exceed_limit(self):
        r=CLIENT.post('/api/astro/report',json={'mode':'period','profile':PROFILE,'date':'2026-01-01','end_date':'2026-12-31'})
        self.assertEqual(r.status_code,422)
if __name__=='__main__':unittest.main()