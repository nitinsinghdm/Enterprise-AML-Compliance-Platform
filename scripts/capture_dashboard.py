"""Capture the real localhost dashboard. Start Streamlit before running this script."""
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width':1600,'height':1500},device_scale_factor=1)
    page.goto('http://127.0.0.1:8501',wait_until='networkidle')
    page.get_by_role('heading',name='Follow the money. Understand the signals.').wait_for()
    page.locator('.js-plotly-plot').last.wait_for()
    page.evaluate('document.fonts.ready')
    page.screenshot(path=str(root/'images/dashboard-overview.png'))
    page.get_by_test_id('stSidebar').get_by_text('Alert explorer',exact=True).click()
    page.get_by_role('heading',name='From signals to investigation.').wait_for()
    page.get_by_text('Customer behavior in the snapshot',exact=True).wait_for()
    page.wait_for_function("Array.from(document.querySelectorAll('[data-testid=stDataFrame] canvas')).some(c => c.getBoundingClientRect().width > 500)")
    page.wait_for_timeout(1200)
    page.screenshot(path=str(root/'images/alert-explorer.png'))
    assert page.get_by_test_id('stException').count() == 0
    page.get_by_test_id('stSidebar').get_by_text('Pipeline & guide',exact=True).click()
    page.get_by_role('heading',name='See how the system works.').wait_for()
    assert page.get_by_test_id('stException').count() == 0
    browser.close()
print('Saved real dashboard screenshots and checked the guide page.')
