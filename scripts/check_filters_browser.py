"""Browser checks for transaction filters, review follow-up and adjustable audio."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
data=json.loads((root/'web/network/data.json').read_text())
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script('''window.peaks=[];window.AudioContext=class {
      state='running';currentTime=0;destination={};resume(){return Promise.resolve()}
      createOscillator(){return {frequency:{value:0},connect(){},start(){},stop(){}}}
      createGain(){return {gain:{setValueAtTime(){},linearRampToValueAtTime(v){window.peaks.push(v)},exponentialRampToValueAtTime(){}},connect(){}}}
    };''')
    page.goto(os.getenv('AML_NETWORK_URL','http://127.0.0.1:8766'),wait_until='networkidle')
    page.locator('#app').wait_for(state='visible')
    assert set(page.locator('#currency option').evaluate_all('els=>els.map(e=>e.value)'))=={'','EUR','USD','GBP'}
    expected=[t for t in data['transactions'] if t['currency']=='USD' and t['status']=='COMPLETED']
    page.select_option('#currency','USD')
    assert page.locator('#payment-count').inner_text()==f'{len(expected):,}'
    chosen=expected[0]
    for key in ['country','kind','channel','direction']:
        page.select_option('#'+key,chosen[key]);expected=[t for t in expected if t[key]==chosen[key]]
        assert page.locator('#payment-count').inner_text()==f'{len(expected):,}'
    page.locator('.transaction-link').first.click()
    assert 'Original amount:' in page.locator('#inspector').inner_text()
    cursor=page.locator('#day').input_value()
    page.locator('#back-payments').click()
    assert page.locator('#payment-count').inner_text()==f"{len(data['transactions']):,}"
    assert page.locator('#day').input_value()==cursor
    assert page.locator('#currency').input_value()==''
    # Full supporting evidence is restored when opening a matching alert.
    page.locator('#reset').click()
    event=data['alerts'][0]
    row=next(t for t in data['transactions'] if t['id'] in event['evidence'])
    page.select_option('#currency',row['currency'])
    page.select_option('#account',event['account'])
    page.select_option('#pattern',event['rule'])
    page.locator('.alert-card').first.click()
    assert page.locator('#currency').input_value()==''
    assert f"{len(event['evidence'])} records" in page.locator('#page-count').inner_text()
    page.select_option('#counterparty-context','incoming')
    assert 'source-account identifier is not present' in page.locator('#counterparty-details').inner_text()
    assert 'not a person’s location' in page.locator('#counterparty-details').inner_text()
    page.locator('input[name="account-review-status"][value="watch"]').check()
    page.locator('input[name="account-review-status"][value="escalated"]').click()
    assert page.locator('input[value="watch"]').is_checked()
    assert 'Add a review note' in page.locator('#review-save-message').inner_text()
    page.locator('#review-note').fill('Review payment purpose and request source records.')
    page.locator('input[value="escalated"]').check()
    assert 'does not send or assign' in page.locator('#review-next-step').inner_text()
    page.locator('[data-view="review"]').click()
    assert 'Escalated for Review' in page.locator('.review-item').first.inner_text()
    page.locator('#test-sound').click()
    assert page.evaluate('Math.max(...window.peaks)')>.2
    page.locator('#alert-volume').fill('20');page.locator('#alert-volume').dispatch_event('input')
    page.evaluate('window.peaks=[]');page.locator('#test-sound').click()
    assert abs(page.evaluate('Math.max(...window.peaks)')-.064)<.0001
    assert page.locator('#volume-value').inner_text()=='20%'
    page.locator('#alert-volume').fill('0');page.evaluate('window.peaks=[]');page.locator('#test-sound').click()
    assert page.evaluate('window.peaks.length')==0
    page.set_viewport_size({'width':390,'height':844})
    page.locator('[data-view="network"]').click()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    browser.close()
print('Filters, complete evidence, return navigation, unknown-source context, escalation rationale and volume checks passed.')
