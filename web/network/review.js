'use strict';
// Browser-local synthetic review workflow. No server writes or bank decisions.
const REVIEW_STATES={unmarked:'Not Marked',watch:'Watch',review:'Under Review',escalated:'Escalated for Review',closed:'Review Closed'};
const REVIEW_NEXT={unmarked:'No follow-up is recorded. Inspect the evidence before choosing a status.',watch:'Monitor future activity and record why this account deserves attention.',review:'Inspect the flagged payments, source of funds and available account context. Record findings in the note.',escalated:'Prepare the evidence and rationale for an authorised senior reviewer. This demo records your intent; it does not send or assign the case.',closed:'Record the outcome and rationale. Closing this local review does not establish that activity is safe.'};
let reviewRecords={},reviewStorageKey=null,reviewStorageAvailable=true,reviewNode=null,investigationView='network';
let audioContext=null,soundEnabled=false,lastReviewClock=null;
function setInvestigationView(view){
 investigationView=view;
 for(const b of document.querySelectorAll('[data-view]')){if(b.dataset.view===view)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');}
 $('workspace').hidden=view!=='network';document.querySelector('.ledger').hidden=view!=='network';$('account-details').hidden=view!=='network';
 $('pattern-overview').hidden=view!=='network';$('review-page').hidden=view!=='review';$('investigation-guide').hidden=view!=='guide';$('method').hidden=view!=='network';
 if(view!=='network')stop();else requestAnimationFrame(resize);
 renderReviewList();
}
window.setInvestigationView=setInvestigationView;
window.inspectNetworkNode=n=>{reviewNode=n;};
window.accountReviewStatus=id=>reviewRecords[id]?.status||'unmarked';
function loadReviewStorage(){
 if(reviewStorageKey)return;
 reviewStorageKey=`northstar-reviews-v1-${hash(JSON.stringify(data.transactions.map(({currency,original_amount,...legacy})=>legacy)))}`;
 try{
  const saved=JSON.parse(localStorage.getItem(reviewStorageKey)||'{}');
  for(const a of data.accounts){const r=saved[a.id];if(r&&Object.hasOwn(REVIEW_STATES,r.status)&&typeof r.note==='string')reviewRecords[a.id]={status:r.status,note:r.note.slice(0,1000),updated:typeof r.updated==='string'?r.updated:'',history:Array.isArray(r.history)?r.history.filter(h=>h&&Object.hasOwn(REVIEW_STATES,h.status)&&typeof h.at==='string').slice(-20):[]};}
 }catch{reviewStorageAvailable=false;}
 storageMessage();draw();
}
function storageMessage(){ $('storage-message').textContent=reviewStorageAvailable?'Saved in this browser only for this synthetic dataset. Export notes to keep a copy.':'Browser storage is unavailable. Marks last only for this page session; export notes before leaving.'; }
function saveReview(id,status,note){
 const previous=reviewRecords[id],at=new Date().toISOString(),history=[...(previous?.history||[])];
 if(previous?.status!==status)history.push({status,at});
 reviewRecords[id]={status,note:note.slice(0,1000),updated:at,history:history.slice(-20)};
 if(status==='unmarked'&&!note.trim())delete reviewRecords[id];
 try{localStorage.setItem(reviewStorageKey,JSON.stringify(reviewRecords));}catch{reviewStorageAvailable=false;}
 storageMessage();renderReviewList();draw();
}
function fact(list,label,value){const wrap=element('div');wrap.append(element('dt',label),element('dd',String(value)));list.append(wrap);}
function renderAccountDetails(){
 const panel=$('account-details'),id=$('account').value;panel.replaceChildren(element('h2','Account details'));
 if(!id){panel.append(element('p','Select an account point or use the Account filter to inspect recorded activity, then mark the account for review.'));return;}
 const account=data.accounts.find(a=>a.id===id);if(!account)return;
 const arrived=data.transactions.filter(t=>t.account===id&&t._time<=cursorTime());
 const completed=arrived.filter(t=>t.status==='COMPLETED');
 const flags=alertsAtCursor().filter(a=>a.account===id);const rules=[...new Set(flags.map(a=>a.rule))];
 panel.append(element('h3',`${id} / ${account.customer}`),element('p',`All recorded activity up to ${utc(cursorTime())}, independent of the graph’s time-window and pattern filters. These totals are flows, not an account balance.`));
 const facts=element('dl',undefined,'account-facts');
 fact(facts,'Arrived payments',fmt.format(arrived.length));fact(facts,'Completed incoming',eur(completed.filter(t=>t.direction==='INCOMING').reduce((s,t)=>s+t.amount,0)));fact(facts,'Completed outgoing',eur(completed.filter(t=>t.direction==='OUTGOING').reduce((s,t)=>s+t.amount,0)));fact(facts,'Distinct rule types',rules.length);
 fact(facts,'Known beneficiary records',new Set(arrived.map(t=>t.beneficiary).filter(Boolean)).size);fact(facts,'Pending / failed',`${arrived.filter(t=>t.status==='PENDING').length} / ${arrived.filter(t=>t.status==='FAILED').length}`);fact(facts,'First arrived payment',arrived[0]?.timestamp.replace('T',' ').replace('Z',' UTC')||'None yet');fact(facts,'Latest arrived payment',arrived.at(-1)?.timestamp.replace('T',' ').replace('Z',' UTC')||'None yet');panel.append(facts);
 panel.append(element('p',`Recorded countries: ${[...new Set(arrived.map(t=>t.country))].join(', ')||'None yet'}. Channels: ${[...new Set(arrived.map(t=>pretty(t.channel)))].join(', ')||'None yet'}. Country codes describe records, not a person’s location.`,'note'));
 if(reviewNode&&reviewNode.account===id&&reviewNode.kind!=='bank'){
  const linked=arrived.filter(t=>reviewNode.kind==='external'?t.beneficiary===reviewNode.id:reviewNode.id.startsWith('UN-IN')?t.direction==='INCOMING':t.direction==='OUTGOING'&&!t.beneficiary);
  panel.append(element('h4',reviewNode.kind==='external'?`Selected beneficiary ${reviewNode.id}`:'Selected unidentified counterparty group'),element('p',`${linked.length} arrived payment record(s) connect this endpoint to ${id}. ${reviewNode.kind==='external'?'This is a beneficiary record, not verified ownership information.':'This groups unresolved endpoints; it does not establish a shared account or identity.'}`));
 }
 panel.append(element('p',flags.some(a=>a.rule==='VELOCITY'&&a.count>=12)||rules.length>=2?'Demo priority: higher review priority (12-payment burst or multiple rule types).':'Demo priority: standard review; no higher-priority trigger at this time.','note'));
 panel.append(element('p',rules.length?`Triggered Patterns: ${rules.map(r=>RULES[r].name).join('; ')}.`:'No rules have triggered for this account at the displayed time. This is not proof that it is safe.'),element('p','Names, account balances, KYC documents, IBANs and verified ownership are not supplied in this public synthetic fixture.','note'));
 const currentReview=reviewRecords[id]||{status:'unmarked',note:''};
 const field=element('fieldset',undefined,'review-status');field.append(element('legend','Mark This Account'));
 for(const [value,label]of Object.entries(REVIEW_STATES)){
  const l=element('label'),input=element('input');input.type='radio';input.name='account-review-status';input.value=value;input.checked=currentReview.status===value;
  input.addEventListener('change',()=>{stop();const text=$('review-note').value;if(['escalated','closed'].includes(value)&&!text.trim()){field.querySelector(`input[value="${reviewRecords[id]?.status||'unmarked'}"]`).checked=true;$('review-save-message').textContent='Add a review note explaining the reason before escalating or closing.';$('review-note').focus();return;}saveReview(id,value,text);renderAccountDetails();$('review-next-step').textContent=REVIEW_NEXT[value];$('review-save-message').textContent=`Saved as ${REVIEW_STATES[value]}. The account is listed in Account Reviews. No external action has been taken.`;});l.append(input,document.createTextNode(label));field.append(l);
 }
 const label=element('label','Review note (synthetic data only, up to 1,000 characters)');label.htmlFor='review-note';
 const note=element('textarea');note.id='review-note';note.maxLength=1000;note.value=currentReview.note;note.addEventListener('focus',stop);
 const save=element('button','Save Review Note');save.addEventListener('click',()=>{saveReview(id,panel.querySelector('input:checked').value,note.value);$('review-save-message').textContent='Review note saved.';});
 const message=element('p','Browser-local demo notes; not shared case management or a compliance audit trail.','note');message.id='review-save-message';message.setAttribute('role','status');
 const next=element('p',REVIEW_NEXT[currentReview.status],'review-next-step');next.id='review-next-step';next.setAttribute('role','status');
 const history=element('details');history.append(element('summary','Local Status History'));
 history.append(element('p','Recent browser-local status changes; not an authenticated or tamper-proof audit trail.','note'));
 for(const entry of (currentReview.history||[]).slice().reverse())history.append(element('p',`${REVIEW_STATES[entry.status]} · ${entry.at.replace('T',' ').replace('Z',' UTC')}`));
 panel.append(field,next,label,note,save,message,history);
 const endpointLabel=element('label','Counterparty Context');endpointLabel.htmlFor='counterparty-context';const endpoint=element('select');endpoint.id='counterparty-context';option(endpoint,'incoming','Unidentified Sources');option(endpoint,'outgoing','Unidentified Recipients');for(const ben of [...new Set(arrived.map(t=>t.beneficiary).filter(Boolean))])option(endpoint,ben,`Recorded Beneficiary ${ben}`);
 const context=element('section',undefined,'counterparty-context');context.id='counterparty-details';
 endpoint.value=reviewNode?.account===id?(reviewNode.kind==='external'?reviewNode.id:reviewNode.id.startsWith('UN-IN')?'incoming':'outgoing'):'incoming';
 function showContext(){const selected=endpoint.value,linked=arrived.filter(t=>selected==='incoming'?t.direction==='INCOMING':selected==='outgoing'?t.direction==='OUTGOING'&&!t.beneficiary:t.beneficiary===selected);context.replaceChildren(element('h4',selected==='incoming'?'Unidentified Sources':selected==='outgoing'?'Unidentified Recipients':selected));context.append(element('p',`${linked.length} payment record(s); ${eur(linked.filter(t=>t.status==='COMPLETED').reduce((sum,t)=>sum+t.amount,0))} completed value in EUR. Countries: ${[...new Set(linked.map(t=>t.country))].join(', ')||'None'}. Source currencies: ${[...new Set(linked.map(t=>t.currency))].join(', ')||'None'}.`));context.append(element('p',linked.length?`First record: ${linked[0].timestamp}. Latest record: ${linked.at(-1).timestamp}. Channels: ${[...new Set(linked.map(t=>pretty(t.channel)))].join(', ')}.`:'No records for this endpoint have arrived at the displayed time.'));context.append(element('p',selected==='incoming'?'The source-account identifier is not present in this public record. A cash deposit may not have a sending account. Other incoming records cannot be attributed to a sender from the available fields.':selected==='outgoing'?'These outgoing records have no beneficiary identifier. Their recipients cannot be resolved from this snapshot.':'This is a recorded beneficiary alias, not independently verified ownership.'));context.append(element('p','Unknown endpoints are grouped for this account and direction only; the group does not mean all payments share one sender. A reviewer would need the original payment reference and authorised originator/beneficiary records to resolve identity. Country is a transaction field, not a person’s location.','note'));}
 endpoint.addEventListener('change',showContext);panel.append(endpointLabel,endpoint,context);showContext();
}
function renderReviewList(){
 if(!data)return;
 const counts=$('review-counts');counts.replaceChildren();for(const [status,label]of Object.entries(REVIEW_STATES)){if(status==='unmarked')continue;const button=element('button',`${label} · ${Object.values(reviewRecords).filter(r=>r.status===status).length}`);button.addEventListener('click',()=>{$('review-filter').value=status;renderReviewList();});counts.append(button);}
 const list=$('review-list');list.replaceChildren();
 for(const [id,r]of Object.entries(reviewRecords).sort((a,b)=>({escalated:3,review:2,watch:1,closed:0,unmarked:-1}[b[1].status]-{escalated:3,review:2,watch:1,closed:0,unmarked:-1}[a[1].status])||b[1].updated.localeCompare(a[1].updated))){
  if($('review-filter').value&&r.status!==$('review-filter').value)continue;
  const item=element('article',undefined,'review-item');const open=element('button',id);open.addEventListener('click',()=>{stop();selectedPayment=null;active=null;reviewNode=null;$('account').value=id;$('pattern').value='';$('status').value='ALL';$('window').value='ALL';clearDetailFilters();setInvestigationView('network');update();$('account-details').scrollIntoView({behavior:'auto'});});
  item.append(open,element('strong',REVIEW_STATES[r.status]),element('span',r.updated?`Saved ${r.updated.replace('T',' ').replace(/\.\d+Z$/,' UTC')}`:''),element('p',REVIEW_NEXT[r.status],'review-next-step'),element('p',r.note||'No review note.'));list.append(item);
 }
}
function tone(high){
 if(!soundEnabled||!audioContext||audioContext.state!=='running'||Number($('alert-volume').value)===0)return;
 const start=audioContext.currentTime;for(let i=0;i<(high?2:1);i++){const oscillator=audioContext.createOscillator(),gain=audioContext.createGain(),at=start+i*.38;oscillator.type='sine';oscillator.frequency.value=high?880:440;gain.gain.setValueAtTime(0,at);gain.gain.linearRampToValueAtTime(.32*Number($('alert-volume').value)/100,at+.02);gain.gain.exponentialRampToValueAtTime(.001,at+.28);oscillator.connect(gain);gain.connect(audioContext.destination);oscillator.start(at);oscillator.stop(at+.3);}
}
function reviewUpdate(){
 loadReviewStorage();const now=cursorTime();
 if(playing&&lastReviewClock!==null&&now>lastReviewClock){
  const arrivedVersions=data.alert_events.filter(a=>a._time>lastReviewClock&&a._time<=now&&alertMatchesDetails(a)&&(!$('account').value||a.account===$('account').value)&&(!$('pattern').value||a.rule===$('pattern').value)&&['ALL','COMPLETED'].includes($('status').value));
  const fresh=arrivedVersions.filter(a=>a.timestamp===a.first_detected);
  const accounts=new Set(arrivedVersions.map(a=>a.account));let high=false;
  for(const id of accounts){const before=new Set(data.alert_events.filter(a=>a.account===id&&a._time<=lastReviewClock).map(a=>a.rule));const after=new Set(data.alert_events.filter(a=>a.account===id&&a._time<=now).map(a=>a.rule));if(before.size<2&&after.size>=2)high=true;}
  const growingBurst=arrivedVersions.some(a=>a.rule==='VELOCITY'&&a.count>=12&&!data.alert_events.some(prior=>prior.id===a.id&&prior._time<=lastReviewClock&&prior.count>=12));
  high=high||growingBurst;
  if(fresh.length||high){
   tone(high);$('alert-announcement').textContent=high?(growingBurst?'Higher review priority: the burst reached 12 completed payments within one hour. Inspect the growing evidence; this does not establish laundering.':'Higher review priority: a second distinct rule has flagged this account. Inspect both patterns; this does not establish laundering.'):`${fresh.length} new review alert(s): ${[...new Set(fresh.map(a=>RULES[a.rule].name))].join(', ')}. Select an alert to inspect its evidence.`;
  }
 }
 lastReviewClock=now;
 $('replay-explainer').textContent=guidedUntil!==null?'Guided example: payments share a line because their endpoints match. The payment count rises as records arrive. At 10 completed payments within one hour, the burst rule triggers and playback pauses for inspection.':$('window').value==='ALL'?'All history: arrived payments remain visible. One path can contain many payment points; the ledger lists each record.':`Rolling ${$('window').value==='3600'?'hour':'24 hours'}: older payments leave this view as the clock advances. A count falling to zero means no payments remain in the selected window, not deletion or a cleared account. Select all history to see earlier records.`;
 renderAccountDetails();renderReviewList();renderPatternCards();
}
window.reviewUpdate=reviewUpdate;
for(const b of document.querySelectorAll('[data-view]'))b.addEventListener('click',()=>setInvestigationView(b.dataset.view));
$('review-filter').addEventListener('change',renderReviewList);
$('sound-toggle').addEventListener('click',async()=>{
 try{if(!soundEnabled){audioContext=audioContext||new (window.AudioContext||window.webkitAudioContext)();await audioContext.resume();soundEnabled=audioContext.state==='running';}else soundEnabled=false;
 $('sound-toggle').textContent=`Alert Sound: ${soundEnabled?'On':'Off'}`;$('sound-toggle').setAttribute('aria-pressed',String(soundEnabled));if(!soundEnabled&&audioContext?.state!=='running')$('sound-help').textContent='Audio is unavailable. Visual alerts remain active.';
 }catch{soundEnabled=false;$('sound-help').textContent='Audio is unavailable in this browser. Visual alerts remain active.';}
});
$('export-reviews').addEventListener('click',()=>{const blob=new Blob([JSON.stringify({synthetic:true,dataset:reviewStorageKey,exported_at:new Date().toISOString(),reviews:reviewRecords},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob),a=element('a');a.href=url;a.download='northstar-demo-review-notes.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});

function reviewPriority(a){const groups=alertsAtCursor().filter(x=>x.account===a.account);return groups.some(x=>x.rule==='VELOCITY'&&x.count>=12)||new Set(groups.map(x=>x.rule)).size>=2?1:0;}
function chooseReviewAlert(alert){stop();guidedUntil=null;setInvestigationView('network');$('window').value='ALL';$('map-mode').value='flagged';selectAlert(alert);$('workspace').scrollIntoView({behavior:'auto'});}
function renderPatternCards(){
 const available=alertsAtCursor().filter(a=>(!$('account').value||a.account===$('account').value)&&a._time>=windowStart()&&alertMatchesDetails(a)&&['ALL','COMPLETED'].includes($('status').value));
 const cards=$('pattern-cards');cards.replaceChildren();
 for(const [code,rule]of Object.entries(RULES)){
  const alerts=available.filter(a=>a.rule===code);const button=element('button',undefined,'pattern-card');button.disabled=!alerts.length;button.style.setProperty('--signal',rule.color);button.append(element('strong',rule.name),element('span',`${alerts.length} alert group(s) · ${new Set(alerts.map(a=>a.account)).size} account(s)`));button.addEventListener('click',()=>chooseReviewAlert([...alerts].sort((a,b)=>reviewPriority(b)-reviewPriority(a)||b._time-a._time)[0]));cards.append(button);
 }
 $('pattern-summary').textContent='Counts follow the account, status, time window and replay cursor. Pattern cards compare all four rules. Review order uses the documented demo priority, then the latest evidence update; it is not a probability of money laundering.';
 $('start-review').disabled=!available.length;
 $('start-review').onclick=()=>chooseReviewAlert([...available].sort((a,b)=>reviewPriority(b)-reviewPriority(a)||b._time-a._time)[0]);
}

$('alert-volume').addEventListener('input',()=>{$('volume-value').textContent=$('alert-volume').value+'%';});
$('test-sound').addEventListener('click',async()=>{try{audioContext=audioContext||new (window.AudioContext||window.webkitAudioContext)();await audioContext.resume();soundEnabled=audioContext.state==='running';$('sound-toggle').textContent=`Alert Sound: ${soundEnabled?'On':'Off'}`;$('sound-toggle').setAttribute('aria-pressed',String(soundEnabled));tone(true);}catch{$('sound-help').textContent='Audio is unavailable. Visual alerts remain active.';}});
