"""Exercise the synthetic analyst workspace against the locally served network."""
import json
import os
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
fixture = json.loads((root / 'web/network/data.json').read_text())
start = datetime.fromisoformat(fixture['transactions'][0]['timestamp'])
url = os.getenv('AML_NETWORK_URL', 'http://127.0.0.1:8766')
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    # Capture Web Audio requests rather than producing sound in the test runner.
    page.add_init_script('''window.testTones=[];window.AudioContext=class {
      state='running';currentTime=0;destination={};resume(){return Promise.resolve();}
      createOscillator(){return {frequency:{value:0},connect(){},start(){window.testTones.push(this.frequency.value)},stop(){}};}
      createGain(){return {gain:{setValueAtTime(){},linearRampToValueAtTime(){},exponentialRampToValueAtTime(){}},connect(){}};}
    };''')
    page.goto(url, wait_until='networkidle')
    page.locator('#app').wait_for(state='visible')
    assert page.locator('#sound-toggle').get_attribute('aria-pressed') == 'false'
    page.select_option('#account', 'AC-001')
    assert 'AC-001 / CU-' in page.locator('#account-details h3').inner_text()
    assert 'not an account balance' in page.locator('#account-details').inner_text()
    page.locator('input[name="account-review-status"][value="watch"]').check()
    page.locator('#account-details').screenshot(path=str(root / 'images/account-review.png'))
    note = '<script>not executable</script> Check source of funds.'
    page.locator('#review-note').fill(note)
    page.get_by_role('button', name='Save Review Note', exact=True).click()
    page.locator('[data-view="review"]').click()
    assert page.locator('#workspace').is_hidden()
    assert note in page.locator('#review-list').inner_text()
    assert page.locator('#review-list script').count() == 0
    with page.expect_download() as download:
        page.locator('#export-reviews').click()
    assert download.value.suggested_filename == 'northstar-demo-review-notes.json'
    page.reload(wait_until='networkidle')
    page.locator('#app').wait_for(state='visible')
    page.locator('[data-view="review"]').click()
    page.get_by_role('button', name='AC-001', exact=True).click()
    assert page.locator('input[value="watch"]').is_checked()
    assert page.locator('#review-note').input_value() == note
    page.locator('input[value="review"]').check()
    page.locator('[data-view="review"]').click()
    page.select_option('#review-filter', 'watch')
    assert page.locator('.review-item').count() == 0
    page.select_option('#review-filter', 'review')
    assert page.locator('.review-item').count() == 1
    page.locator('[data-view="guide"]').click()
    assert page.locator('#investigation-guide').is_visible()
    # Guided playback keeps history and pauses at the first burst, even at high speed.
    page.locator('#watch-demo').click()
    page.select_option('#speed', '3600')
    page.wait_for_function("document.getElementById('replay-state').textContent==='SIMULATION PAUSED'")
    assert page.locator('#window').input_value() == 'ALL'
    assert 'Replay paused' in page.locator('#replay-explainer').inner_text()
    assert int(page.locator('#payment-count').inner_text().replace(',', '')) >= 10
    assert 'Payment Burst' in page.locator('#alerts').inner_text()
    # A first rule sounds low; a second distinct rule on the same account sounds high.
    escalation = next(a for a in fixture['alert_events'] if a['rule']=='VELOCITY' and a['count']>=12)
    first = next(a for a in fixture['alert_events'] if a['id']==escalation['id'])
    page.locator('#sound-toggle').click()
    for event, expected in [(first, [440]), (escalation, [880, 880])]:
        page.locator('[data-view="network"]').click()
        page.locator('#reset').click()
        page.select_option('#account', event['account'])
        seconds = int((datetime.fromisoformat(event['timestamp']) - start).total_seconds())
        page.locator('#day').fill(str(seconds - 1))
        assert page.evaluate('window.testTones.length') == 0
        page.select_option('#speed', '1')
        page.locator('#play').click()
        page.wait_for_function('window.testTones.length>0')
        page.locator('#play').click()
        assert page.evaluate('window.testTones') == expected
        page.evaluate('window.testTones=[]')
    page.locator('#sound-toggle').click()
    assert page.locator('#sound-toggle').get_attribute('aria-pressed') == 'false'
    page.select_option('#window', '3600')
    assert 'not deletion' in page.locator('#replay-explainer').inner_text()
    # Storage denial is disclosed; review remains usable in memory.
    blocked = browser.new_page()
    blocked.add_init_script("Storage.prototype.setItem=function(){throw new Error('blocked')}")
    blocked.goto(url, wait_until='networkidle')
    blocked.locator('#app').wait_for(state='visible')
    blocked.select_option('#account', 'AC-001')
    blocked.locator('input[value="watch"]').check()
    blocked.locator('[data-view="review"]').click()
    assert 'unavailable' in blocked.locator('#storage-message').inner_text()
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.locator('[data-view="review"]').click()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    browser.close()
print('Review browser acceptance passed: marks, notes, persistence, export, guided pause, sound policy and mobile.')
