"""Browser acceptance for the static network. Start `python -m http.server 8766` in web/network."""
import json
import os
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
url=os.getenv('AML_NETWORK_URL','http://127.0.0.1:8766')
fixture=json.loads((root/'web/network/data.json').read_text())
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':1680,'height':1500},reduced_motion='reduce')
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url,wait_until='networkidle')
    page.locator('#app').wait_for(state='visible')
    page.evaluate('document.fonts.ready')
    completed=[t for t in fixture['transactions'] if t['status']=='COMPLETED']
    assert page.locator('#payment-count').text_content()==f'{len(completed):,}'
    assert page.locator('#alert-count').text_content()==str(len(fixture['alerts']))
    assert page.locator('#account-count').text_content()==str(len(fixture['accounts']))
    page.locator('.network-panel').screenshot(path=str(root/'images/network-overview.png'))
    assert page.locator('.pattern-card').count()==4
    assert page.locator('#map-mode').input_value()=='flagged'
    assert 'evidence-linked payments shown' in page.locator('#map-explanation').inner_text()
    total_before=page.locator('#payment-count').inner_text()
    page.select_option('#map-mode','all')
    assert page.locator('#payment-count').inner_text()==total_before
    assert '250 bank accounts' in page.locator('#network-caption').inner_text()
    page.locator('#start-review').click()
    assert page.locator('#account').input_value().startswith('AC-')
    assert page.locator('#map-mode').input_value()=='flagged'
    assert page.locator('#ledger-title').text_content()=='Supporting payments for this flag'
    page.locator('#reset').click()
    page.select_option('#status','ALL')
    assert page.locator('#payment-count').text_content()==f"{len(fixture['transactions']):,}"
    with page.expect_download() as result:
        page.locator('#download').click()
    assert result.value.suggested_filename=='northstar-synthetic-view.csv'
    page.select_option('#status','FAILED')
    assert page.locator('#alert-count').text_content()=='0'
    page.locator('#reset').click()
    for rule in ['STRUCTURING','VELOCITY','RAPID_MOVEMENT','HIGH_RISK_CORRIDOR']:
        page.locator('#reset').click()
        page.select_option('#pattern',rule)
        page.locator('.alert-card').first.click()
        account=page.locator('#account').input_value()
        assert account.startswith('AC-')
        assert page.locator('#ledger-title').text_content()=='Supporting payments for this flag'
        assert 'Rules: northstar-sql-v1' in page.locator('#inspector').text_content()
        assert page.locator('#transactions tr').count()>0
        if rule=='RAPID_MOVEMENT':
            assert 'Context' in page.locator('#transactions').text_content()
            assert 'Counted' in page.locator('#transactions').text_content()
            page.screenshot(path=str(root/'images/network-evidence.png'))
    # Every first alert appears at its actual event second, never before.
    from datetime import datetime
    start = datetime.fromisoformat(fixture['transactions'][0]['timestamp'])
    for rule in ['STRUCTURING','VELOCITY','RAPID_MOVEMENT','HIGH_RISK_CORRIDOR']:
        event=next(a for a in fixture['alert_events'] if a['rule']==rule)
        offset=int((datetime.fromisoformat(event['timestamp'])-start).total_seconds())
        page.locator('#reset').click()
        page.select_option('#account',event['account'])
        page.select_option('#pattern',rule)
        page.locator('#day').fill(str(offset-1))
        assert page.locator('#alert-count').text_content()=='0'
        page.locator('#day').fill(str(offset))
        assert page.locator('#alert-count').text_content()=='1'
        page.locator('.alert-card').first.click()
        assert page.locator('#transactions tr').count()>0
    page.locator('#watch-demo').click()
    page.locator('#play').click()
    assert page.locator('#window').input_value()=='ALL'
    before=int(page.locator('#day').input_value())
    page.locator('#next-event').click()
    assert int(page.locator('#day').input_value())>before
    assert page.locator('#alert-count').text_content()=='0'
    page.locator('#jump').fill(fixture['transactions'][-1]['timestamp'].rstrip('Z'))
    page.locator('#jump').dispatch_event('change')
    assert 'UTC' in page.locator('#day-label').text_content()
    assert page.locator('.lede').evaluate("e=>getComputedStyle(e).textTransform")=='none'
    assert page.locator('h1').evaluate("e=>getComputedStyle(e).textTransform")=='uppercase'
    page.locator('#reset').click()
    page.locator('#day').fill('0')
    assert page.locator('#alert-count').text_content()=='0'
    page.locator('#play').click()
    page.wait_for_function("Number(document.getElementById('day').value)>0")
    page.locator('#play').click()
    page.locator('#reset').click()
    page.locator('#zoom-in').click();page.locator('#fit').click()
    page.locator('#network').focus();page.keyboard.press('ArrowRight');page.keyboard.press('0')
    page.locator('.transaction-link').first.click()
    assert page.locator('#ledger-title').text_content()=='Selected payment'
    assert page.locator('#inspector h3').text_content().startswith('TX-')
    page.locator('#reset').click()
    page.locator('#next').click()
    assert 'page 2' in page.locator('#page-count').text_content()
    # Replay rate scales wall-clock timing while preserving the selected event-time step.
    from datetime import timedelta, timezone
    speed_page=browser.new_page()
    speed_page.goto(url,wait_until='networkidle')
    speed_page.locator('#app').wait_for(state='visible')
    speed_page.clock.install()
    speed_page.clock.pause_at(datetime.now(timezone.utc)+timedelta(seconds=1))
    for rate, expected in [('0.1',1),('0.5',5),('1',10),('1.5',15),('2',20)]:
        speed_page.locator('#reset').click()
        speed_page.locator('#day').fill('0')
        speed_page.select_option('#speed','1')
        speed_page.select_option('#playback-rate',rate)
        speed_page.locator('#play').click()
        speed_page.clock.run_for(10000)
        assert int(speed_page.locator('#day').input_value())==expected,(rate,expected)
        speed_page.locator('#play').click()
        speed_page.clock.run_for(2000)
        assert int(speed_page.locator('#day').input_value())==expected
    speed_page.locator('#day').fill('0')
    speed_page.select_option('#playback-rate','1')
    speed_page.locator('#play').click()
    speed_page.clock.run_for(1000)
    speed_page.select_option('#playback-rate','2')
    speed_page.clock.run_for(1000)
    assert speed_page.locator('#day').input_value()=='3'
    speed_page.locator('#play').click()
    assert speed_page.locator('.intro-note strong').inner_text()=='NOT PROOF OF A CRIME.'
    assert speed_page.locator('[data-view="network"]').inner_text()=='Transaction Network'
    assert speed_page.locator('label[for="playback-rate"]').inner_text().startswith('Playback Speed')
    assert speed_page.locator('.metrics').inner_text().find('Payments in View')>=0
    speed_page.close()
    mobile=browser.new_page(viewport={'width':390,'height':844},reduced_motion='reduce')
    mobile.goto(url,wait_until='networkidle');mobile.locator('#app').wait_for(state='visible')
    assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth')
    mobile.select_option('#pattern','RAPID_MOVEMENT');mobile.locator('.alert-card').first.click()
    assert mobile.locator('#inspector h3').text_content()=='Rapid Money Movement'
    mobile.screenshot(path=str(Path(tempfile.gettempdir())/'northstar-mobile.png'),full_page=True)
    assert not errors,errors
    browser.close()
print('Network browser acceptance passed: totals, filters, evidence, replay, export, pagination, keyboard and mobile.')
