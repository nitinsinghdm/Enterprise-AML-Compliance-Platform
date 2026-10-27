"""Launch: streamlit run dashboard_app.py. Read-only, localhost-only snapshot explorer."""
import pandas as pd
import plotly.express as px
import streamlit as st

from aml.dashboard_data import EXPORT, activity_metrics, filter_activity, load_snapshot

st.set_page_config(page_title='NorthStar | AML Observatory', page_icon='◈', layout='wide')
st.markdown('''<style>
html, body, [data-testid="stApp"] {font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.block-container {padding-top:4rem;max-width:1440px}
[data-testid="stMetric"] {background:#171d18;border:1px solid #354036;padding:20px;border-radius:16px}
[data-testid="stMetricLabel"] {color:#a7b0a5;font-size:13px}
h1 {letter-spacing:-1.6px;font-weight:750!important}
h3 {letter-spacing:-.4px}
button:focus-visible, a:focus-visible {outline:3px solid #d2f783!important;outline-offset:4px}
@media(max-width:640px) {h1 {font-size:2rem!important;letter-spacing:-1px}.block-container {padding-left:1rem;padding-right:1rem}}
.eyebrow {color:#d2f783;font-size:12px;letter-spacing:2px;font-weight:700}
.hero-copy {color:#a7b0a5;font-size:17px;max-width:840px;margin-bottom:28px}
[data-testid="stSidebar"] {border-right:1px solid #354036}
[data-testid="stAlert"] p {color:#f3f5ec}
</style>''', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('## ◈ NorthStar')
    st.caption('AML OBSERVATORY')
    st.caption('01 / Generate · 02 / Validate · 03 / Investigate')
    st.divider()
    page = st.radio('Explore', ['Overview', 'Alert explorer', 'Customer risk', 'Pipeline & guide'], label_visibility='collapsed')
    st.divider()
    mode = st.selectbox('Data source', ['Bundled preview', 'My local exports'], key='data_source')
    st.caption('Synthetic research data · read-only')
    st.button('Reload snapshot', help='Rereads files; it does not run the pipeline or connect to a database.')
    st.caption('No background jobs run in this interface. Each view describes the latest selected snapshot.')
    st.link_button('Read the project walkthrough ↗', 'https://nitinsinghdm.github.io/aml.html')

try:
    snapshot = load_snapshot(mode)
except (OSError, ValueError, KeyError, TypeError) as exc:
    st.error(f'Cannot open this snapshot: {exc}')
    st.info('Choose Bundled preview to explore immediately, or export your database using the commands below.')
    st.code('python -m aml export\npython -m aml train', language='bash')
    st.stop()
f = snapshot['frames']
for warning in snapshot['warnings']:
    st.warning(warning)
st.markdown('<div class="eyebrow">NORTHSTAR BANK / COMPLIANCE ANALYTICS</div>', unsafe_allow_html=True)
st.title({'Overview':'Follow the money. Understand the signals.', 'Alert explorer':'From signals to investigation.',
          'Customer risk':'Understand customer behavior.', 'Pipeline & guide':'See how the system works.'}[page])
st.markdown('<div class="hero-copy">Explore payment activity, explainable monitoring rules and customer risk in one place.</div>', unsafe_allow_html=True)
st.caption(f"{mode.upper()}  ·  Exported {snapshot['manifest']['exported_at'][:19].replace('T', ' ')} UTC  ·  Synthetic data, not live banking activity")

COLORS = ['#d2f783','#6ba5ff','#f7c66b','#e58da9']

def chart(fig):
    fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#a7b0a5'), margin=dict(l=12,r=12,t=16,b=12), height=300,
        legend_title_text='', xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})

if page == 'Overview':
    daily = f['dashboard_daily']
    if daily.empty:
        st.info('No activity in this snapshot. Generate transactions and export again.')
        st.stop()
    with st.expander('Filter activity', expanded=False):
        left, middle, right = st.columns([1,1,1.4])
        countries = left.multiselect('Destination country', sorted(daily.destination_country.unique()), default=sorted(daily.destination_country.unique()))
        channels = middle.multiselect('Channel', sorted(daily.channel.unique()), default=sorted(daily.channel.unique()))
        dates = right.date_input('Date range', (daily.transaction_date.min(), daily.transaction_date.max()))
    selected = filter_activity(daily, countries, channels, dates)
    m = activity_metrics(selected)
    cols = st.columns(4)
    for col,label,value in zip(cols, ['Transactions','Completed volume · EUR','Completion rate','Completed payments'],
                                [f"{m['total']:,}",f"€{m['volume']:,.0f}",f"{m['completion_rate']:.1f}%",f"{m['completed']:,}"]):
        col.metric(label,value)
    st.write('')
    left,right = st.columns([1.65,1])
    with left:
        st.subheader('Payment activity over time')
        st.caption('Completed volume in EUR · fixed synthetic exchange rates')
        series = selected.groupby('transaction_date',as_index=False).completed_amount_eur.sum()
        chart(px.area(series,x='transaction_date',y='completed_amount_eur',color_discrete_sequence=COLORS))
    with right:
        st.subheader('Where payments go')
        st.caption('Completed volume by destination country')
        grouped = selected.groupby('destination_country',as_index=False).completed_amount_eur.sum()
        chart(px.bar(grouped,x='destination_country',y='completed_amount_eur',color_discrete_sequence=COLORS))
    st.divider()
    left,right = st.columns([1.65,1])
    with left:
        st.subheader('Monitoring signals')
        st.caption('Whole snapshot · account/day/rule alert groups; unaffected by activity filters')
        counts = f['alerts'].groupby('rule_code').size().reset_index(name='Alert groups')
        chart(px.bar(counts,x='Alert groups',y='rule_code',orientation='h',color='rule_code',color_discrete_sequence=COLORS).update_layout(showlegend=False))
    with right:
        st.subheader('What am I looking at?')
        st.markdown('''**1. Payments** are generated synthetic banking records.

**2. Rules** flag unusual patterns for review. Multiple rules can flag the same activity.

**3. Risk scores** rank customers using a model trained on the injected scenarios.

Open **Alert explorer** to see the evidence, or **Pipeline & guide** to trace every step.''')
    if selected.empty:
        st.info('No activity matches these filters. Select at least one country and channel.')
    st.download_button('Download filtered daily activity', selected.to_csv(index=False), 'daily_activity.csv', 'text/csv')

elif page == 'Alert explorer':
    alerts = f['alerts']
    rules = st.multiselect('Monitoring rules', sorted(alerts.rule_code.unique()), default=sorted(alerts.rule_code.unique()))
    selected = alerts[alerts.rule_code.isin(rules)]
    a,b,c = st.columns(3)
    a.metric('Alert groups', len(selected))
    b.metric('Customers flagged', selected.customer_id.nunique())
    c.metric('Accounts flagged', selected.account_id.nunique())
    st.caption('These are review candidates, not confirmed money laundering. Alert amounts overlap across rules.')
    explanations = {'STRUCTURING':'Three or more incoming cash deposits of €8,000–<€10,000 on one account/day, totaling at least €24,000.',
        'VELOCITY':'At least 10 completed transactions on an account within a trailing hour.',
        'HIGH_RISK_CORRIDOR':'A cross-border completed payment of at least €10,000 to a HIGH/CRITICAL-rated reference country.',
        'RAPID_MOVEMENT':'An outgoing payment of at least €9,000 within one hour of incoming funds, at 80–120% of the incoming amount.'}
    st.dataframe(selected, hide_index=True, use_container_width=True)
    if not selected.empty:
        selected = selected.reset_index(drop=True)
        row_id = st.selectbox('Inspect an alert', list(selected.index), format_func=lambda i:f"{selected.loc[i,'rule_code']} · {selected.loc[i,'transaction_date']} · customer {selected.loc[i,'customer_id'][:8]}")
        row = selected.loc[row_id]
        st.info(explanations.get(row.rule_code, 'Custom rule'))
        st.markdown(f"**Evidence:** {int(row.evidence_count)} transaction(s) in the rule's evidence count; €{row.amount_eur:,.2f} associated with this alert group.")
        st.caption('For velocity, evidence is the peak trailing-hour count; the amount covers triggering rows only.')
        st.subheader('Customer behavior in the snapshot')
        st.dataframe(f['customer_features'][f['customer_features'].customer_id == row.customer_id], hide_index=True, use_container_width=True)
    else:
        st.info('No alerts match the selected rules.')
    st.download_button('Download selected alert groups',selected.to_csv(index=False),'alerts.csv','text/csv')

elif page == 'Customer risk':
    scores = f['customer_risk_scores']
    if scores.empty:
        st.info('No model scores available. Run python -m aml train after exporting your data.')
        st.stop()
    st.warning('Scores measure synthetic scenario patterns, not proven real-world AML risk. Training rows are in-sample; only holdout metrics evaluate unseen customers.')
    split = st.selectbox('Evaluation group', ['All customers','holdout','train'], key='evaluation_group')
    selected = scores if split == 'All customers' else scores[scores.evaluation_split == split]
    a,b,c = st.columns(3)
    a.metric('Scored customers',len(selected))
    b.metric('High score band',int((selected.risk_band=='HIGH').sum()))
    c.metric('Median score',f'{selected.risk_score.median():.1f}' if len(selected) else '—')
    left,right = st.columns(2)
    with left:
        st.subheader('Score distribution')
        chart(px.histogram(selected,x='risk_score',nbins=20,color_discrete_sequence=COLORS))
    with right:
        st.subheader('What the model used')
        importance = snapshot['metrics'].get('feature_importance',{})
        chart(px.bar(pd.DataFrame({'Feature':list(importance),'Importance':list(importance.values())}).sort_values('Importance'),
                     x='Importance',y='Feature',orientation='h',color_discrete_sequence=COLORS))
    st.dataframe(selected.sort_values('risk_score',ascending=False),hide_index=True,use_container_width=True)
    with st.expander('Read the model evaluation'):
        st.json(snapshot['metrics'])

else:
    st.subheader('Your pipeline, in plain language')
    st.image('images/pipeline.svg', use_container_width=True)
    st.markdown('''**Generate → validate → monitor → explore.** The Python generator creates synthetic payments. PostgreSQL checks each record and keeps rejected rows for inspection. SQL rules find suspicious patterns. Exports feed this interface, the customer model, Spark and optional Snowflake/Looker integrations.''')
    st.subheader('Evidence in this snapshot')
    batches = f['pipeline_batches']; checks = f['quality_checks']
    statuses = [
        {'Stage':'Banking data & ingestion','Evidence':f'{len(batches)} recorded load batches' if len(batches) else 'Batch evidence unavailable in this export'},
        {'Stage':'SQL data quality','Evidence':f'{len(checks)} checks; {int(checks.violations.sum())} violations' if len(checks) else 'Quality evidence unavailable in this export'},
        {'Stage':'Analytics export','Evidence':f"{len(f['dashboard_daily'])} daily groups; {len(f['alerts'])} alert groups"},
        {'Stage':'Customer model','Evidence':f"{len(f['customer_risk_scores'])} scores available"},
        {'Stage':'Spark execution','Evidence':'Not checked by this snapshot viewer; see terminal output and Parquet files'},
        {'Stage':'Snowflake / Looker Studio','Evidence':'External setup; connection/publication not checked here'},
    ]
    st.dataframe(pd.DataFrame(statuses),hide_index=True,use_container_width=True)
    with st.expander('Load history and rejected-row counts',expanded=True):
        st.dataframe(batches,hide_index=True,use_container_width=True)
    with st.expander('SQL quality checks'):
        st.dataframe(checks,hide_index=True,use_container_width=True)
    st.subheader('Run it yourself')
    st.markdown('**Step 1 — Explore now:** select Bundled preview. No database, Java or cloud credentials needed.')
    st.markdown('**Step 2 — Run your pipeline:** configure an isolated demo PostgreSQL database using the README, then run these commands in another terminal.')
    st.code('python -m aml demo --customers 200 --per-account 30\npython -m aml validate\npython -m aml export\npython -m aml train',language='bash')
    st.markdown('**Step 3 — See your results:** choose My local exports, then Reload snapshot. The source and export timestamp are displayed at the top of every page.')
    st.caption(f'Local export directory: {EXPORT}')
    st.markdown('**What was added:** transaction generation, audited ingestion, SQL monitoring, Spark transformations, model training/scoring, Snowflake loading, tests and documentation. Your original banking schema and reference data were retained.')
