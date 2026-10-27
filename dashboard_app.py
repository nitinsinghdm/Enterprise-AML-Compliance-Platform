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
h1, h2, h3 {font-family:Inter,sans-serif!important;font-weight:650!important;letter-spacing:-.045em;line-height:1.12!important}
h1 {font-size:clamp(2rem,3.3vw,3.4rem)!important;max-width:1000px;padding-bottom:1rem!important}
h3 {font-size:1.4rem!important;letter-spacing:-.03em}
[data-testid="stMarkdownContainer"] p {line-height:1.65}
[data-testid="stMetricValue"] {font-size:2rem;font-weight:500;letter-spacing:-.04em;font-variant-numeric:tabular-nums}
[data-testid="stCaptionContainer"] {font-size:.8rem;line-height:1.6}
[data-testid="stSidebar"] h2 {font-size:1.6rem!important}
[data-testid="stSidebar"] label p {font-size:.875rem}
[data-baseweb="tag"], [data-baseweb="tag"] span {color:#182014!important}
button:focus-visible, a:focus-visible {outline:3px solid #d2f783!important;outline-offset:4px}
@media(max-width:640px) {h1 {font-size:2rem!important;letter-spacing:-1px}.block-container {padding-left:1rem;padding-right:1rem}}
.eyebrow {color:#d2f783;font-size:11px;letter-spacing:.13em;font-weight:500}
.hero-copy {color:#a7b0a5;font-size:17px;max-width:840px;margin-bottom:28px}
[data-testid="stSidebar"] {border-right:1px solid #354036}
[data-testid="stAlert"] p {color:#f3f5ec}
</style>''', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('## ◈ NorthStar')
    st.caption('AML OBSERVATORY')
    st.caption('Understand payments. Spot unusual patterns.')
    st.divider()
    page = st.radio('Explore', ['Overview', 'Alert explorer', 'Customer risk', 'Pipeline & guide'], format_func=lambda name: {'Overview':'Payment overview','Alert explorer':'What needs a closer look','Customer risk':'Customer scores','Pipeline & guide':'How this demo works'}[name], label_visibility='collapsed')
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
st.title({'Overview':'A clearer picture of payment activity.', 'Alert explorer':'Why were these payments flagged?',
          'Customer risk':'Which customers need a closer look?', 'Pipeline & guide':'From sample payments to useful clues.'}[page])
intro = {
    'Overview': 'This demo shows how a bank could find unusual payment patterns. Start with the payments, then explore the clues that might need a person to review them.',
    'Alert explorer': 'A flag is a clue, not proof of wrongdoing. Choose a pattern below to see why the system noticed it and what a reviewer should check next.',
    'Customer risk': 'These scores show how closely a customer’s activity matches the unusual patterns built into this demo. A higher score suggests a closer look, not a verdict.',
    'Pipeline & guide': 'Everything here starts with made-up customers and payments. Follow the four steps to understand how those records become charts, flags and scores.'
}
st.markdown(f'<div class="hero-copy">{intro[page]}</div>', unsafe_allow_html=True)
st.caption(f"{mode.upper()}  ·  Exported {snapshot['manifest']['exported_at'][:19].replace('T', ' ')} UTC  ·  Synthetic data, not live banking activity")

RULE_NAMES = {'STRUCTURING':'Repeated cash deposits', 'VELOCITY':'Many payments in a short time',
              'HIGH_RISK_CORRIDOR':'Large payments to higher-risk countries', 'RAPID_MOVEMENT':'Money moving in and out quickly'}
RULE_STORIES = {
    'STRUCTURING': ('Several cash deposits add up to a larger amount.', 'Check where the money came from and whether there is a reasonable explanation for splitting the deposits.'),
    'VELOCITY': ('Many payments happened close together.', 'Check whether this pace is normal for the account and whether the customer recognises the payments.'),
    'HIGH_RISK_CORRIDOR': ('A large payment went abroad to a country marked higher-risk in the demo.', 'Check the payment purpose and recipient. The demo country rating is not evidence of wrongdoing.'),
    'RAPID_MOVEMENT': ('Money left the account soon after a similar amount arrived.', 'Check the source and purpose of both payments. A legitimate transfer may also look like this.')
}
COLORS = ['#d2f783','#6ba5ff','#f7c66b','#e58da9']

def chart(fig):
    fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif',size=12,color='#a7b0a5'), margin=dict(l=12,r=12,t=16,b=12), height=300,
        legend_title_text='', xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})

if page == 'Overview':
    with st.container(border=True):
        st.markdown('**What this dashboard is for**')
        st.write('Banks review unusual activity to help detect money laundering — hiding where money came from. This project demonstrates that process using made-up data. It does not move or block money.')
        st.caption('Read it in order: ① See the payments below → ② Explore the flags → ③ Compare customer scores.')
    st.subheader('1. Start with the payments')
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
    for col,label,value in zip(cols, ['Payments recorded','Money successfully sent','Payments successful','Successful payments'],
                                [f"{m['total']:,}",f"€{m['volume']:,.0f}",f"{m['completion_rate']:.1f}%",f"{m['completed']:,}"]):
        col.metric(label,value)
    st.caption('These numbers follow your filters. Money values are shown in euros using fixed demo exchange rates.')
    left,right = st.columns([1.65,1])
    with left:
        st.subheader('When was money sent?')
        st.caption('Completed volume in EUR · fixed synthetic exchange rates')
        series = selected.groupby('transaction_date',as_index=False).completed_amount_eur.sum()
        chart(px.area(series,x='transaction_date',y='completed_amount_eur',labels={'transaction_date':'Date','completed_amount_eur':'Money sent (€)'},color_discrete_sequence=COLORS))
        if not series.empty:
            peak = series.loc[series.completed_amount_eur.idxmax()]
            st.caption(f"Largest daily total in this selection: €{peak.completed_amount_eur:,.0f} on {peak.transaction_date:%d %b %Y}. A peak alone does not prove suspicious activity.")
    with right:
        st.subheader('Where did the money go?')
        st.caption('Completed volume by destination country')
        grouped = selected.groupby('destination_country',as_index=False).completed_amount_eur.sum()
        grouped['Country'] = grouped.destination_country.map(lambda code: {'DE':'Germany','CN':'China','RU':'Russia'}.get(code, code))
        chart(px.bar(grouped,x='Country',y='completed_amount_eur',labels={'completed_amount_eur':'Money sent (€)'},color_discrete_sequence=COLORS))
    st.divider()
    left,right = st.columns([1.65,1])
    with left:
        st.subheader('2. See what caught the system’s attention')
        st.caption('All saved data, regardless of the filters above. Each flag groups one account, one day and one rule. One payment can contribute to more than one flag.')
        counts = f['alerts'].groupby('rule_code').size().reset_index(name='Alert groups')
        counts['Rule'] = counts.rule_code.map(RULE_NAMES)
        chart(px.bar(counts,x='Alert groups',y='Rule',orientation='h',color='Rule',color_discrete_sequence=COLORS).update_layout(showlegend=False))
    with right:
        st.subheader('3. Understand the flags')
        st.markdown('''**A flag means “take a closer look.”** It does not mean someone committed a crime.

The system checks for repeated cash deposits, fast payment bursts, large payments abroad and money moving quickly through an account.

**Next:** open **What needs a closer look** in the sidebar. Pick a flag to see the reason and suggested review steps.''')
    if selected.empty:
        st.info('No activity matches these filters. Select at least one country and channel.')
    st.download_button('Download filtered daily activity', selected.to_csv(index=False), 'daily_activity.csv', 'text/csv')

elif page == 'Alert explorer':
    alerts = f['alerts']
    rules = st.multiselect('Which patterns do you want to explore?', sorted(alerts.rule_code.unique()), default=sorted(alerts.rule_code.unique()), format_func=lambda code: RULE_NAMES.get(code, code))
    selected = alerts[alerts.rule_code.isin(rules)]
    a,b,c = st.columns(3)
    a.metric('Flags to review', len(selected))
    b.metric('Customers involved', selected.customer_id.nunique())
    c.metric('Accounts involved', selected.account_id.nunique())
    st.caption('These are review candidates, not confirmed money laundering. Alert amounts overlap across rules.')
    explanations = {'STRUCTURING':'Three or more incoming cash deposits of €8,000–<€10,000 on one account/day, totaling at least €24,000.',
        'VELOCITY':'At least 10 completed transactions on an account within a trailing hour.',
        'HIGH_RISK_CORRIDOR':'A cross-border completed payment of at least €10,000 to a HIGH/CRITICAL-rated reference country.',
        'RAPID_MOVEMENT':'An outgoing payment of at least €9,000 within one hour of incoming funds, at 80–120% of the incoming amount.'}
    table = selected.assign(Pattern=selected.rule_code.map(RULE_NAMES))
    st.dataframe(table[['Pattern','transaction_date','evidence_count','amount_eur']].rename(columns={
        'transaction_date':'Date', 'evidence_count':'Payments in evidence', 'amount_eur':'Amount linked to flag (€)'}),
        hide_index=True, use_container_width=True)
    st.caption('Amounts can overlap between flags. Do not add them together as a total of suspicious money.')
    if not selected.empty:
        selected = selected.reset_index(drop=True)
        row_id = st.selectbox('Choose a flag to understand', list(selected.index), format_func=lambda i:f"{RULE_NAMES.get(selected.loc[i,'rule_code'], selected.loc[i,'rule_code'])} · {selected.loc[i,'transaction_date']} · customer {selected.loc[i,'customer_id'][:8]}")
        row = selected.loc[row_id]
        reason, next_step = RULE_STORIES.get(row.rule_code, ('An unusual pattern was detected.', 'Review the underlying records.'))
        with st.container(border=True):
            st.subheader('What happened')
            st.write(reason)
            st.markdown('**What a reviewer could check next**')
            st.write(next_step)
        with st.expander('Exact rule and calculation'):
            st.write(explanations.get(row.rule_code, 'Custom rule'))
        st.markdown(f"**Evidence:** {int(row.evidence_count)} transaction(s) in the rule's evidence count; €{row.amount_eur:,.2f} associated with this alert group.")
        st.caption('For velocity, evidence is the peak trailing-hour count; the amount covers triggering rows only.')
        with st.expander('Customer data and original record IDs'):
            st.dataframe(f['customer_features'][f['customer_features'].customer_id == row.customer_id], hide_index=True, use_container_width=True)
            st.dataframe(selected, hide_index=True, use_container_width=True)
    else:
        st.info('No alerts match the selected rules.')
    st.download_button('Download selected alert groups',selected.to_csv(index=False),'alerts.csv','text/csv')

elif page == 'Customer risk':
    scores = f['customer_risk_scores']
    if scores.empty:
        st.info('No model scores available. Run python -m aml train after exporting your data.')
        st.stop()
    st.info('A score is a review aid, not the chance that someone committed a crime. This model has only been tested on made-up data.')
    split = st.selectbox('Evaluation group', ['All customers','holdout','train'], key='evaluation_group', format_func=lambda group: {'All customers':'All customers', 'holdout':'Test customers — not used for learning', 'train':'Practice customers — used for learning'}[group])
    selected = scores if split == 'All customers' else scores[scores.evaluation_split == split]
    a,b,c = st.columns(3)
    a.metric('Scored customers',len(selected))
    b.metric('High score band',int((selected.risk_band=='HIGH').sum()))
    c.metric('Median score',f'{selected.risk_score.median():.1f}' if len(selected) else '—')
    left,right = st.columns(2)
    with left:
        st.subheader('How many customers have each score?')
        st.caption('Higher scores mean a closer match to the demo’s unusual patterns.')
        chart(px.histogram(selected,x='risk_score',nbins=20,color_discrete_sequence=COLORS))
    with right:
        st.subheader('Which information influenced the model?')
        st.caption('Overall model importance, not an explanation of any individual customer.')
        importance = snapshot['metrics'].get('feature_importance',{})
        chart(px.bar(pd.DataFrame({'Feature':[name.replace('_',' ').capitalize() for name in importance],'Importance':list(importance.values())}).sort_values('Importance'),
                     x='Importance',y='Feature',orientation='h',color_discrete_sequence=COLORS))
    with st.expander('See individual customer scores'):
        st.dataframe(selected.sort_values('risk_score',ascending=False),hide_index=True,use_container_width=True)
    with st.expander('Read the model evaluation'):
        st.json(snapshot['metrics'])

else:
    st.subheader('Four steps. One clear purpose.')
    steps = st.columns(4)
    for column, title, description in zip(steps,
        ['1. Create sample data', '2. Check the records', '3. Look for patterns', '4. Help a person review'],
        ['Make fictional customers and payments, including unusual examples.',
         'Check that records are valid and keep track of rejected rows.',
         'Apply rules and calculate customer scores from the activity.',
         'Show clear clues and supporting data. A person decides what they mean.']):
        with column:
            st.markdown(f'**{title}**')
            st.write(description)
    st.subheader('The technical path')
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
    with st.expander('Load history and rejected-row counts'):
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
