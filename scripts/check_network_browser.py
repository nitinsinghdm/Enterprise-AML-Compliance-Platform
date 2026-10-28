"""Browser acceptance for the static network. Start `python -m http.server 8766` in web/network."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
url=os.getenv('AML_NETWORK_URL','http://127.0.0.1:8766')
fixture=json.loads((root/'web/network/data.json').read_text())
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':1680,'height':1250},reduced_motion='reduce')
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url,wait_until='networkidle')
    page.locator('#app').wait_for(state='visible')
    page.evaluate('document.fonts.ready')
    completed=[t for t in fixture['transactions'] if t['status']=='COMPLETED']
    assert page.locator('#payment-count').inner_text()==f'{len(completed):,}'
    assert page.locator('#alert-count').inner_text()==str(len(fixture['alerts']))
    assert page.locator('#account-count').inner_text()=='100'
    page.screenshot(path=str(root/'images/network-overview.png'),full_page=False)
    page.select_option('#status','ALL')
    assert page.locator('#payment-count').inner_text()=='2,110'
    with page.expect_download() as result:
        page.locator('#download').click()
    assert result.value.suggested_filename=='northstar-synthetic-view.csv'
    page.select_option('#status','FAILED')
    assert page.locator('#alert-count').inner_text()=='0'
    page.locator('#reset').click()
    for rule in ['STRUCTURING','VELOCITY','RAPID_MOVEMENT','HIGH_RISK_CORRIDOR']:
        page.locator('#reset').click()
        page.select_option('#pattern',rule)
        page.locator('.alert-card').first.click()
        account=page.locator('#account').input_value()
        assert account.startswith('AC-')
        assert page.locator('#ledger-title').inner_text()=='Supporting payments for this flag'
        assert 'Rules: northstar-sql-v1' in page.locator('#inspector').inner_text()
        assert page.locator('#transactions tr').count()>0
        if rule=='RAPID_MOVEMENT':
            assert 'Context' in page.locator('#transactions').inner_text()
            assert 'Counted' in page.locator('#transactions').inner_text()
            page.screenshot(path=str(root/'images/network-evidence.png'))
    page.locator('#reset').click()
    page.locator('#day').fill('0')
    assert page.locator('#alert-count').inner_text()=='0'
    page.locator('#play').click()
    page.wait_for_function("Number(document.getElementById('day').value)>0")
    page.locator('#play').click()
    page.locator('#reset').click()
    page.locator('#zoom-in').click();page.locator('#fit').click()
    page.locator('#network').focus();page.keyboard.press('ArrowRight');page.keyboard.press('0')
    page.locator('.transaction-link').first.click()
    assert page.locator('#ledger-title').inner_text()=='Selected payment'
    assert page.locator('#inspector h3').inner_text().startswith('TX-')
    page.locator('#reset').click()
    page.locator('#next').click()
    assert 'page 2' in page.locator('#page-count').inner_text()
    mobile=browser.new_page(viewport={'width':390,'height':844},reduced_motion='reduce')
    mobile.goto(url,wait_until='networkidle');mobile.locator('#app').wait_for(state='visible')
    assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth')
    mobile.select_option('#pattern','RAPID_MOVEMENT');mobile.locator('.alert-card').first.click()
    assert mobile.locator('#inspector h3').inner_text()=='Rapid money movement'
    mobile.screenshot(path='/private/tmp/northstar-mobile.png',full_page=True)
    assert not errors,errors
    browser.close()
print('Network browser acceptance passed: totals, filters, evidence, replay, export, pagination, keyboard and mobile.')
